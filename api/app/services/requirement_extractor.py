"""Production requirement extraction with a lazy GLiNER2.5-small model.

The extractor owns semantic candidate discovery, deterministic enrichment, and
normalisation.  Relevance matching consumes the resulting ``JobRequirement``
objects but does not know how they were produced.  Model loading is lazy and
per-process; inference is serialised because the deployment target is a small
CPU VPS.
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from app.schemas.application import JobRequirement
from app.services.relevance_taxonomy import ALIAS_TO_CANONICAL, TAXONOMY

logger = logging.getLogger(__name__)

DEFAULT_GLINER2_MODEL = "fastino/gliner2.5-small-v1"
DEFAULT_GLINER2_REVISION = "cab1bddfd30fda7b803a4691c41f90378a2d517a"
REQUIREMENT_EXTRACTOR_VERSION = "gliner2.5-small-v1"
REQUIREMENT_EXTRACTION_ERROR = "Unable to extract job requirements"
MAX_REQUIREMENTS = 40
DEFAULT_CHUNK_SIZE = 384
DEFAULT_CHUNK_OVERLAP = 64


class Importance(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    UNKNOWN = "unknown"


class RequirementExtractionError(ValueError):
    """Raised when the configured GLiNER extractor cannot produce a result."""

    def __init__(self, message: str = REQUIREMENT_EXTRACTION_ERROR) -> None:
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class Constraint:
    """A deterministic constraint attached to one source requirement."""

    kind: str
    value: int | float | str | None
    source_text: str
    operator: str | None = None
    maximum: int | float | None = None
    values: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Requirement:
    """The extractor's implementation-independent canonical requirement."""

    id: str
    source_text: str
    source_start: int | None
    source_end: int | None
    type: str
    importance: Importance
    concepts: tuple[str, ...] = ()
    constraints: tuple[Constraint, ...] = ()
    confidence: float = 0.0
    extractor: str = "unknown"
    extractor_version: str = "unknown"


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """A complete extraction result with provenance for persistence/debugging."""

    requirements: tuple[Requirement, ...]
    extractor: str
    extractor_version: str
    status: str = "primary"
    source_hash: str = ""
    warnings: tuple[str, ...] = ()
    inference_path: str = "short"


class RequirementExtractor(Protocol):
    """Boundary consumed by the relevance service."""

    def extract(self, role: str, job_description: str) -> list[JobRequirement]: ...


class EntityModel(Protocol):
    """The narrow model API used by GLiNER and by mocked unit tests."""

    def extract_entities(self, text: str, labels: Mapping[str, str], **kwargs: Any) -> Mapping[str, Any]: ...


MODEL_LABELS: dict[str, str] = {
    "candidate_requirement": (
        "A complete sentence or bullet from a job posting stating what a candidate must, should, or will be able "
        "to do. Include qualifications and implicit requirements expressed as responsibilities. Return the whole "
        "sentence or bullet. Exclude company descriptions, compensation, benefits, location prose, legal boilerplate, "
        "section headings, and isolated technology names."
    ),
    "hard_skill": "A named technical skill, programming language, tool, platform, framework, or method expected from a candidate.",
    "experience_requirement": "A statement about years of experience, ownership, seniority, or work performed by a candidate.",
    "education_requirement": "An education, degree, academic, or study requirement for a candidate.",
    "certification_requirement": "A professional certification, license, or credential expected from a candidate.",
    "responsibility": "A candidate responsibility or capability the job expects the person to perform.",
    "preferred_requirement": "A preferred, optional, nice-to-have, bonus, or otherwise non-mandatory candidate requirement.",
    "quantitative_constraint": "An explicit numeric candidate requirement such as years of experience or a measurable threshold.",
    "domain_knowledge": "A domain, industry, or subject-matter knowledge requirement for a candidate.",
}

_REQUIREMENT_LABELS = frozenset({"candidate_requirement", "requirement", "preferred_requirement"})
_CONCEPT_LABELS = frozenset(
    {
        "hard_skill",
        "experience_requirement",
        "education_requirement",
        "certification_requirement",
        "responsibility",
        "quantitative_constraint",
        "domain_knowledge",
    }
)
_LABEL_TYPE: dict[str, str] = {
    "hard_skill": "hard_skill",
    "experience_requirement": "quantitative",
    "education_requirement": "education",
    "certification_requirement": "certification",
    "responsibility": "responsibility",
    "quantitative_constraint": "quantitative",
    "domain_knowledge": "other",
}
_CONCEPT_VALUE_LABELS = frozenset(
    {"hard_skill", "education_requirement", "certification_requirement", "domain_knowledge"}
)

_REQUIRED_RE = re.compile(
    r"(?:\b(?:must(?:\s+have|\s+be able to)?|require(?:s|d)?|required qualifications?|mandatory|essential|shall)\b|"
    r"\bnon[- ]negotiable\b|\bminimum\s+qualifications?\b|\bwhat\s+(?:we\s+look\s+for|you\s+bring)\b)",
    re.IGNORECASE,
)
_PREFERRED_RE = re.compile(
    r"\b(?:preferred|preferably|nice\s+to\s+have|good\s+to\s+have|a\s+plus|bonus|desirable|"
    r"advantageous|beneficial|extra\s+credit|optional)\b",
    re.IGNORECASE,
)
_NEGATED_RE = re.compile(
    r"\b(?:not\s+required|not\s+necessary|not\s+mandatory|not\s+(?:a\s+)?requirement|"
    r"not\s+needed|no\s+.+?\s+required)\b",
    re.IGNORECASE,
)
_NUMBER_PATTERN = r"(?:\d+(?:\.\d+)?|zero|one|two|three|four|five|six|seven|eight|nine|ten)"
_YEARS_RE = re.compile(
    rf"\b(?:(?P<qualifier>at\s+least|minimum(?:\s+of)?|min(?:imum)?|more\s+than|over)\s+)?"
    rf"(?P<number>{_NUMBER_PATTERN})"
    rf"(?:\s*(?:[-–—]|to)\s*(?P<maximum>{_NUMBER_PATTERN}))?"
    rf"\s*(?:\+|or\s+more)?\s+(?P<unit>years?|yrs?)\b",
    re.IGNORECASE,
)
_DEGREE_RE = re.compile(
    r"(?<!\w)(?:ph\.?d\.?|doctorate|doctoral|master(?:'|’)s?|msc|m\.?s\.?|mba|"
    r"bachelor(?:'|’)s?|bsc|b\.?s\.?|b\.?a\.?|undergraduate|associate(?:'|’)s?|a\.?a\.?)"
    r"(?!\w)",
    re.IGNORECASE,
)
_CERTIFICATION_RE = re.compile(
    r"\b(?:certification|certificate|certified|license|licensed|credential|"
    r"cissp|ccna|ccnp|ccie|cka|ckad|cks|pmp|comptia|itil)\b",
    re.IGNORECASE,
)
_RESPONSIBILITY_RE = re.compile(
    r"\b(?:build|design|develop|lead|own|manage|operate|deliver|maintain|drive|"
    r"implement|coordinate|communicate|collaborate|work|partner|mentor|support)\b",
    re.IGNORECASE,
)
_ELIGIBILITY_RE = re.compile(
    r"\b(?:authorized\s+to\s+work|work\s+authorization|eligible\s+to\s+work|"
    r"right\s+to\s+work|visa\s+sponsorship|sponsor(?:ship)?|must\s+reside|"
    r"must\s+be\s+located|reside\s+in)\b",
    re.IGNORECASE,
)
_COMPENSATION_RE = re.compile(
    r"\b(?:salary|compensation|pay\s+range|hourly\s+rate|annual\s+pay|base\s+pay|"
    r"equity|stock\s+options?|commission|sign[- ]on\s+bonus|bonus\s+target|"
    r"target\s+bonus|total\s+rewards)\b",
    re.IGNORECASE,
)
_BENEFITS_RE = re.compile(
    r"\b(?:benefits?\s+package|health\s+insurance|medical\s+insurance|dental\s+insurance|"
    r"vision\s+insurance|401\s*\(?k\)?|retirement\s+(?:plan|benefits?)|paid\s+time\s+off|"
    r"\bpto\b|parental\s+leave|wellness|perks)\b",
    re.IGNORECASE,
)
_LEGAL_RE = re.compile(
    r"\b(?:equal\s+(?:employment\s+)?opportunity|eeo|affirmative\s+action|"
    r"reasonable\s+accommodation|protected\s+(?:veteran|class)|discrimination|"
    r"harassment|privacy\s+(?:notice|policy)|diversity\s+statement)\b",
    re.IGNORECASE,
)
_LOCATION_RE = re.compile(
    r"\b(?:remote|hybrid|on[- ]site|onsite|work\s+from\s+home|located\s+in|"
    r"based\s+in|in[- ]office|office\s+location)\b",
    re.IGNORECASE,
)
_COMPANY_START_RE = re.compile(
    r"^(?:about\s+(?:us|the\s+company|our\s+team)|we\s+are\s+a\b|we['’]re\s+a\b|"
    r"our\s+company\b|our\s+mission\b|our\s+vision\b|founded\s+in\b|"
    r"headquartered\s+in\b|we\s+build\b|we\s+provide\b|join\s+our\s+team\b)",
    re.IGNORECASE,
)

_REQUIRED_HEADINGS = {
    "requirements",
    "requirement",
    "candidate requirements",
    "candidate requirements and skills",
    "qualifications",
    "qualification",
    "minimum requirements",
    "basic requirements",
    "core qualifications",
    "minimum qualifications",
    "basic qualifications",
    "required qualifications",
    "required experience",
    "required skills",
    "must have",
    "must haves",
    "what you bring",
    "what youll bring",
    "what you need",
    "what we look for",
    "your qualifications",
    "skills",
    "experience",
    "key responsibilities",
    "responsibilities",
    "what you will do",
    "what youll do",
}
_PREFERRED_HEADINGS = {
    "preferred",
    "preferred experience",
    "preferred qualifications",
    "preferred skills",
    "desired skills",
    "desired qualifications",
    "additional qualifications",
    "nice to have",
    "nice to haves",
    "nice to have qualifications",
    "good to have",
    "bonus qualifications",
    "bonus",
}
_EXCLUDED_HEADINGS = {
    "about us",
    "about the company",
    "company description",
    "company overview",
    "company profile",
    "our mission",
    "our values",
    "who we are",
    "benefits",
    "benefits and perks",
    "perks",
    "compensation",
    "salary",
    "pay",
    "total rewards",
    "equal opportunity",
    "equal employment opportunity",
    "eeo statement",
    "legal",
    "privacy",
    "diversity",
}
_LOCATION_HEADINGS = {"location", "locations", "work arrangement", "remote work", "where you work"}


@dataclass(frozen=True, slots=True)
class _RawSpan:
    label: str
    text: str
    start: int | None
    end: int | None
    confidence: float


@dataclass(frozen=True, slots=True)
class _SourceUnit:
    start: int
    end: int
    text: str
    is_heading: bool
    section_kind: str | None
    heading_text: str | None
    heading_start: int | None


@dataclass(frozen=True, slots=True)
class _ChunkUnit:
    start: int
    end: int
    text: str
    heading_start: int | None


@dataclass(frozen=True, slots=True)
class _Chunk:
    start: int
    end: int
    text: str


def _source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalise(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _word_count(value: str) -> int:
    return len(re.findall(r"\S+", value))


def _coerce_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _trim_range(source: str, start: int, end: int, *, bullet: bool = True) -> tuple[int, int]:
    while start < end and source[start].isspace():
        start += 1
    if bullet and start < end and source[start] in "-*•▪‣":
        start += 1
        while start < end and source[start].isspace():
            start += 1
    while end > start and source[end - 1].isspace():
        end -= 1
    return start, end


def _find_text_span(source: str, value: str, cursor: int = 0) -> tuple[int | None, int | None]:
    if not value:
        return None, None
    exact = source.find(value, cursor)
    if exact >= 0:
        return exact, exact + len(value)
    folded_source = source.casefold()
    folded_value = value.casefold()
    folded = folded_source.find(folded_value, cursor)
    if folded >= 0:
        return folded, folded + len(value)
    return None, None


def _heading_kind(value: str) -> str | None:
    stripped = value.strip(" -*#\t").rstrip(":").strip()
    normalized = _normalise(stripped).replace("’", "'").replace("'", "")
    if not stripped or len(stripped) > 100 or len(stripped.split()) > 12:
        return None
    if normalized in _EXCLUDED_HEADINGS:
        return "excluded"
    if normalized in _LOCATION_HEADINGS:
        return "location"
    if normalized in _PREFERRED_HEADINGS:
        return "preferred"
    if normalized in _REQUIRED_HEADINGS:
        return "required"
    if value.rstrip().endswith(":") and not re.search(r"[.!?]$", stripped):
        return "neutral"
    return None


def _is_heading_text(value: str) -> bool:
    return _heading_kind(value) is not None


def _source_units(source: str) -> list[_SourceUnit]:
    raw: list[tuple[int, int, str, str | None]] = []
    for match in re.finditer(r"[^\n]+", source):
        start, end = _trim_range(source, match.start(), match.end())
        if start >= end:
            continue
        text = source[start:end]
        raw.append((start, end, text, _heading_kind(text)))

    units: list[_SourceUnit] = []
    current_kind: str | None = None
    current_heading: str | None = None
    current_heading_start: int | None = None
    for start, end, text, own_kind in raw:
        is_heading = own_kind is not None
        if is_heading:
            current_kind = own_kind
            current_heading = text.rstrip(":").strip()
            current_heading_start = start
            units.append(
                _SourceUnit(
                    start=start,
                    end=end,
                    text=text,
                    is_heading=True,
                    section_kind=own_kind,
                    heading_text=current_heading,
                    heading_start=current_heading_start,
                )
            )
        else:
            units.append(
                _SourceUnit(
                    start=start,
                    end=end,
                    text=text,
                    is_heading=False,
                    section_kind=current_kind,
                    heading_text=current_heading,
                    heading_start=current_heading_start,
                )
            )
    return units


def _sentence_units(unit: _SourceUnit, source: str) -> list[_SourceUnit]:
    """Split a line into sentence contexts without losing section metadata."""

    if unit.is_heading:
        return [unit]
    matches = list(_SENTENCE_RE.finditer(unit.text))
    if len(matches) <= 1:
        return [unit]
    sentences: list[_SourceUnit] = []
    for match in matches:
        start, end = _trim_range(source, unit.start + match.start(), unit.start + match.end(), bullet=False)
        if start < end:
            sentences.append(
                _SourceUnit(
                    start=start,
                    end=end,
                    text=source[start:end],
                    is_heading=False,
                    section_kind=unit.section_kind,
                    heading_text=unit.heading_text,
                    heading_start=unit.heading_start,
                )
            )
    return sentences or [unit]


def _unit_for_offset(source: str, offset: int | None) -> _SourceUnit | None:
    if offset is None:
        return None
    for unit in _source_units(source):
        for sentence in _sentence_units(unit, source):
            if sentence.start <= offset < sentence.end:
                return sentence
    return None


def _overlap(left: _RawSpan, right: _RawSpan) -> int:
    if left.start is None or left.end is None or right.start is None or right.end is None:
        return 0
    return max(0, min(left.end, right.end) - max(left.start, right.start))


_CONCEPT_CONTEXT_WINDOW = 160
_CLAUSE_BREAK_RE = re.compile(r"[.!?;\n]")
_SENTENCE_RE = re.compile(r"(?:[^.!?]|\.(?=\d))+(?:[.!?]+(?=\s|$)|$)")


def _span_is_near(
    source: str,
    anchor: _RawSpan,
    concept: _RawSpan,
    unit: _SourceUnit | None,
) -> bool:
    """Limit concept attachment to the candidate's local clause."""

    if _overlap(anchor, concept) > 0:
        return True
    if (
        anchor.start is None
        or anchor.end is None
        or concept.start is None
        or concept.end is None
        or unit is None
        or not (unit.start <= concept.start < unit.end)
    ):
        return False
    if concept.start >= anchor.end:
        gap_start, gap_end = anchor.end, concept.start
    elif anchor.start >= concept.end:
        gap_start, gap_end = concept.end, anchor.start
    else:
        return False
    if gap_end - gap_start > _CONCEPT_CONTEXT_WINDOW:
        return False
    return _CLAUSE_BREAK_RE.search(source[gap_start:gap_end]) is None


def _candidate_anchors(candidate: _RawSpan, raw_spans: Sequence[_RawSpan]) -> tuple[_RawSpan, ...]:
    """Recover the short model span that may have been sentence-expanded."""

    anchors = tuple(
        span
        for span in raw_spans
        if span.label in _REQUIREMENT_LABELS and _overlap(candidate, span) > 0
    )
    return anchors or (candidate,)


def _concept_context(
    source: str,
    candidate: _RawSpan,
    anchors: Sequence[_RawSpan],
    unit: _SourceUnit | None,
) -> str:
    """Return candidate text plus bounded context for deterministic enrichment."""

    pieces = [candidate.text]
    for anchor in anchors:
        if anchor.start is None or anchor.end is None:
            continue
        lower = max(unit.start if unit else 0, anchor.start - _CONCEPT_CONTEXT_WINDOW)
        upper = min(unit.end if unit else len(source), anchor.end + _CONCEPT_CONTEXT_WINDOW)
        if lower < upper:
            pieces.append(source[lower:upper])
    return " ".join(dict.fromkeys(piece.strip() for piece in pieces if piece.strip()))


def _coerce_raw_spans(source: str, result: Mapping[str, Any], offset: int = 0) -> list[_RawSpan]:
    entities = result.get("entities", result)
    if not isinstance(entities, Mapping):
        raise ValueError("GLiNER2 result did not contain an entities mapping")

    spans: list[_RawSpan] = []
    for label, values in entities.items():
        if isinstance(values, Mapping) or isinstance(values, str):
            values = [values]
        if not isinstance(values, Sequence):
            continue
        cursor = 0
        for value in values:
            if isinstance(value, Mapping):
                raw_text = value.get("text")
                raw_start = value.get("start")
                raw_end = value.get("end")
                confidence = value.get("confidence", value.get("score", 0.0))
            else:
                raw_text = value
                raw_start = None
                raw_end = None
                confidence = 0.0
            if not isinstance(raw_text, str) or not raw_text.strip():
                continue
            try:
                start = int(raw_start) if raw_start is not None else None
                end = int(raw_end) if raw_end is not None else None
            except (TypeError, ValueError):
                start = end = None
            if start is None or end is None or start < 0 or end <= start or end > len(source):
                start, end = _find_text_span(source, raw_text, cursor)
            if start is not None and end is not None:
                extracted = source[start:end]
                if _normalise(extracted) != _normalise(raw_text):
                    start, end = _find_text_span(source, raw_text, cursor)
            if start is not None and end is not None:
                cursor = end
                raw_text = source[start:end]
            spans.append(
                _RawSpan(
                    label=str(label).casefold().replace("-", "_"),
                    text=source[start:end] if start is not None and end is not None else raw_text.strip(),
                    start=start + offset if start is not None else None,
                    end=end + offset if end is not None else None,
                    confidence=_coerce_confidence(confidence),
                )
            )
    return spans


def _dedupe_spans(spans: Iterable[_RawSpan]) -> list[_RawSpan]:
    ordered = sorted(
        spans,
        key=lambda span: (
            span.start if span.start is not None else 10**12,
            -(span.end - span.start) if span.start is not None and span.end is not None else 0,
            -span.confidence,
        ),
    )
    kept: list[_RawSpan] = []
    for candidate in ordered:
        duplicate: int | None = None
        for index, existing in enumerate(kept):
            if candidate.label != existing.label:
                continue
            if _normalise(candidate.text) == _normalise(existing.text):
                duplicate = index
                break
            overlap = _overlap(candidate, existing)
            candidate_length = max(1, (candidate.end or 0) - (candidate.start or 0))
            existing_length = max(1, (existing.end or 0) - (existing.start or 0))
            if overlap and overlap / min(candidate_length, existing_length) >= 0.8:
                duplicate = index
                break
        if duplicate is None:
            kept.append(candidate)
            continue
        existing = kept[duplicate]
        if candidate.confidence > existing.confidence:
            kept[duplicate] = candidate
    return kept


def _excluded_reason(text: str, section_kind: str | None) -> str | None:
    if section_kind == "excluded":
        return "excluded_section" if not _ELIGIBILITY_RE.search(text) else None
    if section_kind == "location" and _LOCATION_RE.search(text) and not _ELIGIBILITY_RE.search(text):
        return "non_eligibility_location"
    if _COMPENSATION_RE.search(text):
        return "compensation"
    if _BENEFITS_RE.search(text):
        return "benefits"
    if _LEGAL_RE.search(text) and not _ELIGIBILITY_RE.search(text):
        return "legal_boilerplate"
    if _LOCATION_RE.search(text) and not _ELIGIBILITY_RE.search(text):
        return "non_eligibility_location"
    if _COMPANY_START_RE.search(text):
        return "company_description"
    return None


def _span_units(source: str, span: _RawSpan) -> list[_SourceUnit]:
    if span.start is None or span.end is None:
        return []
    result: list[_SourceUnit] = []
    for unit in _source_units(source):
        for sentence in _sentence_units(unit, source):
            if max(0, min(span.end, sentence.end) - max(span.start, sentence.start)) > 0:
                result.append(sentence)
    return result


def _expand_requirement_to_sentence(source: str, span: _RawSpan) -> _RawSpan:
    """Restore the complete sentence when the model returns a short cue span."""

    units = _span_units(source, span)
    if len(units) != 1 or units[0].is_heading:
        return span
    unit = units[0]
    if _normalise(span.text) == _normalise(unit.text):
        return span
    # Preferred labels frequently contain only the named skill (for example
    # ``Kubernetes``) while the importance cue lives in its sentence.  The
    # full source sentence is the useful atomic requirement and preserves the
    # cue for deterministic enrichment.
    if span.label == "preferred_requirement" or any(
        cue.search(unit.text) for cue in (_REQUIRED_RE, _PREFERRED_RE, _NEGATED_RE)
    ):
        return _RawSpan(span.label, unit.text, unit.start, unit.end, span.confidence)
    return span


def _trim_heading_from_span(source: str, span: _RawSpan) -> _RawSpan:
    units = _span_units(source, span)
    non_headings = [unit for unit in units if not unit.is_heading]
    if len(units) > 1 and len(non_headings) == 1:
        unit = non_headings[0]
        return _RawSpan(span.label, unit.text, unit.start, unit.end, span.confidence)
    if span.start is not None and span.end is not None:
        start, end = _trim_range(source, span.start, span.end)
        return _RawSpan(span.label, source[start:end], start, end, span.confidence)
    return span


def _importance(source_text: str, section_kind: str | None, label: str) -> Importance:
    if _NEGATED_RE.search(source_text):
        return Importance.UNKNOWN
    if _REQUIRED_RE.search(source_text):
        return Importance.REQUIRED
    if _PREFERRED_RE.search(source_text) or label == "preferred_requirement":
        return Importance.PREFERRED
    if section_kind == "preferred":
        return Importance.PREFERRED
    if section_kind == "required":
        return Importance.REQUIRED
    return Importance.UNKNOWN


_WORD_NUMBERS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _number_value(value: str) -> int | float:
    normalized = value.casefold()
    if normalized in _WORD_NUMBERS:
        return _WORD_NUMBERS[normalized]
    if re.fullmatch(r"\d+", normalized):
        return int(normalized)
    return float(normalized)


def _constraints(candidate_text: str, context_text: str, label: str) -> tuple[Constraint, ...]:
    # A short concept span should not inherit a number or degree from an
    # unrelated clause on the same source line. Full candidate sentences do.
    context = context_text if _normalise(candidate_text) == _normalise(context_text) else candidate_text
    constraints: list[Constraint] = []
    years = _YEARS_RE.search(context)
    if years:
        try:
            qualifier = _normalise(years.group("qualifier") or "")
            operator = "gt" if qualifier in {"more than", "over"} else "min"
            maximum_text = years.group("maximum")
            maximum = _number_value(maximum_text) if maximum_text else None
            if maximum is not None:
                operator = "range"
            constraints.append(
                Constraint(
                    kind="years_experience",
                    value=_number_value(years.group("number")),
                    source_text=context[years.start() : years.end()],
                    operator=operator,
                    maximum=maximum,
                )
            )
        except (KeyError, TypeError, ValueError):
            pass
    degree = _DEGREE_RE.search(context)
    if degree:
        value = degree.group(0).casefold().replace("’", "'")
        compact = value.replace(".", "").replace(" ", "")
        if "ph" in compact or "doctor" in compact:
            level = "doctorate"
        elif "master" in value or compact in {"ms", "msc", "mba"}:
            level = "master"
        elif "bachelor" in value or "undergraduate" in value or compact in {"bs", "bsc", "ba"}:
            level = "bachelor"
        else:
            level = "associate"
        constraints.append(Constraint("degree_level", level, context[degree.start() : degree.end()]))
    certification = _CERTIFICATION_RE.search(context)
    if label == "certification_requirement" or certification:
        if certification:
            constraints.append(Constraint("certification", "mentioned", context[certification.start() : certification.end()]))
    unique: dict[tuple[object, ...], Constraint] = {}
    for constraint in constraints:
        unique[(constraint.kind, str(constraint.value), constraint.operator, constraint.maximum, constraint.values)] = constraint
    return tuple(unique.values())


def _taxonomy_concepts(text: str) -> list[tuple[str, str]]:
    found: list[tuple[int, int, str, str]] = []
    folded = _normalise(text)
    for alias, canonical in sorted(ALIAS_TO_CANONICAL.items(), key=lambda item: (-len(item[0]), item[0])):
        match = re.search(rf"(?<![\w]){re.escape(_normalise(alias))}(?![\w])", folded)
        if match:
            found.append((match.start(), -len(alias), canonical, TAXONOMY[canonical][0]))
    found.sort(key=lambda item: (item[0], item[1], item[2]))
    deduped: dict[str, str] = {}
    for _start, _length, canonical, kind in found:
        deduped[canonical] = kind
    return list(deduped.items())


def _requirement_type(
    label: str,
    context_text: str,
    taxonomy: Sequence[tuple[str, str]],
    constraints: Sequence[Constraint],
) -> str:
    if any(constraint.kind == "degree_level" for constraint in constraints):
        return "education"
    if any(constraint.kind == "certification" for constraint in constraints):
        return "certification"
    if any(constraint.kind == "years_experience" for constraint in constraints):
        return "quantitative"
    if label in _LABEL_TYPE:
        return _LABEL_TYPE[label]
    if _RESPONSIBILITY_RE.search(context_text):
        return "responsibility"
    if taxonomy:
        return taxonomy[0][1]
    return "other"


def _concept_values(candidate: _RawSpan, attached: Iterable[_RawSpan], context_text: str) -> tuple[str, ...]:
    values = [canonical for canonical, _kind in _taxonomy_concepts(context_text)]
    for span in sorted(attached, key=lambda item: item.start if item.start is not None else 10**12):
        if span.label not in _CONCEPT_VALUE_LABELS:
            continue
        normalized = _normalise(span.text)
        value = ALIAS_TO_CANONICAL.get(normalized, normalized)
        if value and value not in values:
            values.append(value)
    if not values and candidate.label in _CONCEPT_VALUE_LABELS:
        normalized = _normalise(candidate.text)
        value = ALIAS_TO_CANONICAL.get(normalized, normalized)
        if value:
            values.append(value)
    return tuple(values)


def _concept_group_constraint(context_text: str, concepts: Sequence[str]) -> Constraint | None:
    """Represent explicit AND/OR skill alternatives without creating spans."""

    values = tuple(
        dict.fromkeys(
            concept
            for concept in concepts
            if concept in TAXONOMY and TAXONOMY[concept][0] in {"hard_skill", "certification"}
        )
    )
    if len(values) < 2:
        return None
    if re.search(r"\b(?:one\s+of|either|or)\b", context_text, re.IGNORECASE):
        operator = "any"
    elif re.search(r"\band\b", context_text, re.IGNORECASE):
        operator = "all"
    else:
        return None
    return Constraint(
        kind="concept_group",
        value=operator,
        source_text=context_text,
        operator=operator,
        values=values,
    )


def _usable_requirement_span(source: str, span: _RawSpan) -> _RawSpan | None:
    candidate = _expand_requirement_to_sentence(source, _trim_heading_from_span(source, span))
    if not candidate.text.strip() or _is_heading_text(candidate.text):
        return None
    units = _span_units(source, candidate)
    if any(_excluded_reason(item.text, item.section_kind) for item in units if not item.is_heading):
        return None
    return candidate


def _requirements_from_spans(
    source: str,
    raw_spans: Iterable[_RawSpan],
    *,
    extractor: str,
    extractor_version: str,
    inference_path: str,
) -> ExtractionResult:
    spans = _dedupe_spans(raw_spans)
    requirement_spans = [
        candidate
        for span in spans
        if span.label in _REQUIREMENT_LABELS
        for candidate in [_usable_requirement_span(source, span)]
        if candidate is not None
    ]
    concept_spans = [span for span in spans if span.label in _CONCEPT_LABELS]

    # Typed semantic spans are also candidate evidence. Add their containing
    # source unit when the model did not return a complete candidate span for
    # that unit (common for isolated preferred skills).
    candidates: list[_RawSpan] = []
    seen_units: set[tuple[int, int]] = set()
    for candidate in requirement_spans:
        for unit in _span_units(source, candidate):
            if not unit.is_heading:
                seen_units.add((unit.start, unit.end))
    for span in concept_spans:
        unit = _unit_for_offset(source, span.start)
        if unit is None or unit.is_heading or (unit.start, unit.end) in seen_units:
            continue
        fallback = _usable_requirement_span(
            source,
            _RawSpan("requirement", unit.text, unit.start, unit.end, span.confidence),
        )
        if fallback is not None:
            candidates.append(fallback)
            seen_units.add((unit.start, unit.end))
    requirement_spans = _dedupe_spans((*requirement_spans, *candidates))

    requirements: list[Requirement] = []
    for span in sorted(
        requirement_spans,
        key=lambda value: (
            value.start if value.start is not None else 10**12,
            value.end if value.end is not None else 10**12,
        ),
    ):
        candidate = _trim_heading_from_span(source, span)
        if not candidate.text.strip():
            continue
        units = _span_units(source, candidate)
        unit = _unit_for_offset(source, candidate.start)
        context_text = unit.text if unit is not None and len(units) == 1 else candidate.text
        section_kind = unit.section_kind if unit else None
        if any(_excluded_reason(item.text, item.section_kind) for item in units if not item.is_heading):
            continue
        if _is_heading_text(candidate.text):
            continue
        constraints = _constraints(candidate.text, context_text, candidate.label)
        anchors = _candidate_anchors(candidate, spans)
        concept_context = _concept_context(source, candidate, anchors, unit)
        attached = [
            item
            for item in concept_spans
            if any(_span_is_near(source, anchor, item, unit) for anchor in anchors)
        ]
        concepts = _concept_values(candidate, attached, concept_context)
        concept_group = _concept_group_constraint(candidate.text, concepts)
        if concept_group is not None:
            constraints = (*constraints, concept_group)
        taxonomy = _taxonomy_concepts(concept_context)
        requirements.append(
            Requirement(
                id=f"req-{len(requirements) + 1:03d}",
                source_text=candidate.text,
                source_start=candidate.start,
                source_end=candidate.end,
                type=_requirement_type(candidate.label, context_text, taxonomy, constraints),
                importance=_importance(context_text, section_kind, candidate.label),
                concepts=concepts,
                constraints=constraints,
                confidence=candidate.confidence,
                extractor=extractor,
                extractor_version=extractor_version,
            )
        )

    return ExtractionResult(
        requirements=_dedupe_requirements(requirements),
        extractor=extractor,
        extractor_version=extractor_version,
        source_hash=_source_hash(source),
        inference_path=inference_path,
    )


def _importance_rank(value: Importance) -> int:
    return {Importance.UNKNOWN: 0, Importance.PREFERRED: 1, Importance.REQUIRED: 2}[value]


def _requirement_duplicate(left: Requirement, right: Requirement) -> bool:
    if _normalise(left.source_text) == _normalise(right.source_text):
        return True
    if left.source_start is not None and left.source_end is not None and right.source_start is not None and right.source_end is not None:
        overlap = max(0, min(left.source_end, right.source_end) - max(left.source_start, right.source_start))
        shorter = max(1, min(left.source_end - left.source_start, right.source_end - right.source_start))
        if overlap / shorter >= 0.8:
            return True
    return (
        len(left.concepts) == 1
        and len(right.concepts) == 1
        and left.concepts[0] == right.concepts[0]
        and left.type in {"hard_skill", "education", "certification", "quantitative"}
        and right.type == left.type
    )


def _merge_requirements(left: Requirement, right: Requirement) -> Requirement:
    preferred = left if _importance_rank(left.importance) >= _importance_rank(right.importance) else right
    source = preferred if preferred.confidence >= max(left.confidence, right.confidence) - 0.05 else left
    if len(right.source_text) > len(source.source_text) and _importance_rank(right.importance) == _importance_rank(preferred.importance):
        source = right
    constraints: list[Constraint] = list(left.constraints)
    for constraint in right.constraints:
        identity = (constraint.kind, str(constraint.value), constraint.operator, constraint.maximum, constraint.values)
        existing_identities = {
            (item.kind, str(item.value), item.operator, item.maximum, item.values)
            for item in constraints
        }
        if identity not in existing_identities:
            constraints.append(constraint)
    concepts = tuple(dict.fromkeys((*left.concepts, *right.concepts)))
    return Requirement(
        id=left.id,
        source_text=source.source_text,
        source_start=source.source_start,
        source_end=source.source_end,
        type=left.type if left.type != "other" else right.type,
        importance=preferred.importance,
        concepts=concepts,
        constraints=tuple(constraints),
        confidence=max(left.confidence, right.confidence),
        extractor=left.extractor,
        extractor_version=left.extractor_version,
    )


def _dedupe_requirements(requirements: Iterable[Requirement]) -> tuple[Requirement, ...]:
    merged: list[Requirement] = []
    for requirement in requirements:
        match = next((index for index, existing in enumerate(merged) if _requirement_duplicate(existing, requirement)), None)
        if match is None:
            merged.append(requirement)
        else:
            merged[match] = _merge_requirements(merged[match], requirement)
    normalized: list[Requirement] = []
    for index, requirement in enumerate(
        sorted(
            merged,
            key=lambda value: (
                value.source_start if value.source_start is not None else 10**12,
                value.source_end if value.source_end is not None else 10**12,
            ),
        ),
        1,
    ):
        if len(normalized) >= MAX_REQUIREMENTS:
            break
        normalized.append(
            Requirement(
                id=f"req-{index:03d}",
                source_text=requirement.source_text,
                source_start=requirement.source_start,
                source_end=requirement.source_end,
                type=requirement.type,
                importance=requirement.importance,
                concepts=requirement.concepts,
                constraints=requirement.constraints,
                confidence=requirement.confidence,
                extractor=requirement.extractor,
                extractor_version=requirement.extractor_version,
            )
        )
    return tuple(normalized)


def _sentence_parts(unit: _SourceUnit, source: str, chunk_size: int) -> list[_ChunkUnit]:
    if unit.is_heading or _word_count(unit.text) <= max(80, chunk_size // 2):
        return [_ChunkUnit(unit.start, unit.end, unit.text, unit.heading_start)]
    matches = list(_SENTENCE_RE.finditer(unit.text))
    parts: list[_ChunkUnit] = []
    for match in matches:
        start, end = _trim_range(source, unit.start + match.start(), unit.start + match.end(), bullet=False)
        if start < end:
            parts.append(_ChunkUnit(start, end, source[start:end], unit.heading_start))
    if not parts:
        parts = [_ChunkUnit(unit.start, unit.end, unit.text, unit.heading_start)]
    expanded: list[_ChunkUnit] = []
    for part in parts:
        if _word_count(part.text) <= chunk_size:
            expanded.append(part)
            continue
        words = list(re.finditer(r"\S+", part.text))
        for offset in range(0, len(words), chunk_size):
            selected = words[offset : offset + chunk_size]
            start = part.start + selected[0].start()
            end = part.start + selected[-1].end()
            expanded.append(_ChunkUnit(start, end, source[start:end], part.heading_start))
    return expanded


def _document_chunks(source: str, chunk_size: int, chunk_overlap: int) -> list[_Chunk]:
    units = [part for unit in _source_units(source) for part in _sentence_parts(unit, source, chunk_size)]
    if not units:
        return []
    chunks: list[_Chunk] = []
    index = 0
    while index < len(units):
        first = index
        words = 0
        last = index
        while last < len(units):
            unit_words = _word_count(units[last].text)
            if last > first and words + unit_words > chunk_size:
                break
            words += unit_words
            last += 1
        context_start = units[first].heading_start if units[first].heading_start is not None else units[first].start
        end = units[last - 1].end
        chunks.append(_Chunk(context_start, end, source[context_start:end]))
        if last >= len(units):
            break
        next_index = last
        overlap_words = 0
        while next_index > first and overlap_words < chunk_overlap:
            next_index -= 1
            overlap_words += _word_count(units[next_index].text)
        # A single source unit can fill a chunk. Never rewind to the same
        # unit, otherwise overlap bookkeeping loops forever on long bullets.
        index = max(first + 1, next_index)
    return chunks


def requirements_from_model_output(
    source: str,
    result: Mapping[str, Any],
    *,
    extractor: str = "gliner2",
    extractor_version: str = REQUIREMENT_EXTRACTOR_VERSION,
    inference_path: str = "short",
) -> ExtractionResult:
    """Convert one model response into normalized canonical requirements."""

    return _requirements_from_spans(
        source,
        _coerce_raw_spans(source, result),
        extractor=extractor,
        extractor_version=extractor_version,
        inference_path=inference_path,
    )


def _constraint_dict(constraint: Constraint) -> dict[str, Any]:
    if constraint.kind in {"years_experience", "degree_level"}:
        result: dict[str, Any] = {"kind": constraint.kind, "minimum": constraint.value}
        if constraint.operator and constraint.operator != "min":
            result["operator"] = constraint.operator
        if constraint.maximum is not None:
            result["maximum"] = constraint.maximum
        return result
    if constraint.kind == "concept_group":
        return {
            "kind": constraint.kind,
            "operator": constraint.operator or constraint.value,
            "values": list(constraint.values),
        }
    return {"kind": constraint.kind, "value": constraint.value}


def to_job_requirements(result: ExtractionResult) -> list[JobRequirement]:
    """Adapt the canonical extractor result to the existing matcher contract."""

    requirements: list[JobRequirement] = []
    for item in result.requirements:
        canonical_values = [value for value in item.concepts if value in TAXONOMY]
        canonical = canonical_values[0] if len(canonical_values) == 1 else None
        constraints = [_constraint_dict(constraint) for constraint in item.constraints]
        primary_constraint = constraints[0] if constraints else None
        requirements.append(
            JobRequirement(
                id=item.id,
                text=item.source_text,
                normalized=_normalise(item.source_text),
                canonical=canonical,
                type=item.type,  # type: ignore[arg-type]
                required=item.importance is Importance.REQUIRED,
                weight={Importance.REQUIRED: 2.0, Importance.PREFERRED: 1.0, Importance.UNKNOWN: 0.75}[item.importance],
                constraint=primary_constraint,
                importance=item.importance.value,
                concepts=list(item.concepts),
                constraints=constraints,
                source_start=item.source_start,
                source_end=item.source_end,
                confidence=item.confidence,
                extractor=item.extractor,
                extractor_version=item.extractor_version,
            )
        )
    if not requirements:
        raise RequirementExtractionError()
    return requirements


class Gliner2RequirementExtractor:
    """Lazy, serialized GLiNER2.5-small inference for production use."""

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_GLINER2_MODEL,
        revision: str | None = DEFAULT_GLINER2_REVISION,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        model: EntityModel | None = None,
    ) -> None:
        if model_name != DEFAULT_GLINER2_MODEL:
            raise ValueError(f"only {DEFAULT_GLINER2_MODEL} is supported")
        if chunk_size <= chunk_overlap or chunk_overlap < 0:
            raise ValueError("chunk_size must be greater than non-negative chunk_overlap")
        self.model_name = model_name
        self.revision = revision
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._model = model
        self._model_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self.last_inference_path = "short"

    def load(self) -> EntityModel:
        if self._model is not None:
            return self._model
        with self._model_lock:
            if self._model is not None:
                return self._model
            try:
                from gliner2 import AutoExtractor

                kwargs: dict[str, Any] = {"map_location": "cpu"}
                if self.revision:
                    kwargs["revision"] = self.revision
                model = AutoExtractor.from_pretrained(self.model_name, **kwargs)
                eval_method = getattr(model, "eval", None)
                if callable(eval_method):
                    eval_method()
                self._model = model
            except Exception as exc:
                logger.exception("gliner2_requirement_model_load_failed", extra={"model": self.model_name})
                raise RequirementExtractionError() from exc
        return self._model

    def extract_result(self, role: str, job_description: str) -> ExtractionResult:
        del role  # Role titles are context, not candidate source text.
        source = job_description or ""
        if not source.strip():
            raise RequirementExtractionError()
        with self._inference_lock:
            model = self.load()
            try:
                word_count = _word_count(source)
                if word_count > self.chunk_size:
                    long_method = getattr(model, "extract_entities_long", None)
                    if callable(long_method):
                        # GLiNER2 batches its own overlapping chunks in one
                        # model call. Returned spans are document-relative;
                        # section-aware normalization below still applies the
                        # source heading and boilerplate rules.
                        raw = long_method(
                            source,
                            MODEL_LABELS,
                            chunk_size=self.chunk_size,
                            chunk_overlap=self.chunk_overlap,
                            batch_size=8,
                            num_workers=0,
                            include_confidence=True,
                            include_spans=True,
                            overlap_policy="flat",
                        )
                        spans = _coerce_raw_spans(source, raw)
                    else:
                        # Keep a sentence/section-aware fallback for model
                        # doubles and future model adapters without a native
                        # long-document API.
                        chunks = _document_chunks(source, self.chunk_size, self.chunk_overlap)
                        spans = []
                        for chunk in chunks:
                            raw = model.extract_entities(
                                chunk.text,
                                MODEL_LABELS,
                                include_confidence=True,
                                include_spans=True,
                                overlap_policy="flat",
                            )
                            spans.extend(_coerce_raw_spans(chunk.text, raw, offset=chunk.start))
                    self.last_inference_path = "long"
                    result = _requirements_from_spans(
                        source,
                        spans,
                        extractor="gliner2",
                        extractor_version=f"{self.model_name}@{self.revision or 'default'}",
                        inference_path="long",
                    )
                else:
                    raw = model.extract_entities(
                        source,
                        MODEL_LABELS,
                        include_confidence=True,
                        include_spans=True,
                        overlap_policy="flat",
                    )
                    self.last_inference_path = "short"
                    result = requirements_from_model_output(
                        source,
                        raw,
                        extractor="gliner2",
                        extractor_version=f"{self.model_name}@{self.revision or 'default'}",
                        inference_path="short",
                    )
            except RequirementExtractionError:
                raise
            except Exception as exc:
                logger.exception("gliner2_requirement_extraction_failed", extra={"model": self.model_name})
                raise RequirementExtractionError() from exc
            if not result.requirements:
                raise RequirementExtractionError()
            return result

    def extract(self, role: str, job_description: str) -> list[JobRequirement]:
        return to_job_requirements(self.extract_result(role, job_description))


_extractor: RequirementExtractor | None = None
_extractor_factory_lock = threading.Lock()


def get_requirement_extractor() -> RequirementExtractor:
    """Return the process-local lazy extractor singleton."""

    global _extractor
    if _extractor is not None:
        return _extractor
    with _extractor_factory_lock:
        if _extractor is None:
            from app.config import get_settings

            settings = get_settings()
            _extractor = Gliner2RequirementExtractor(
                revision=settings.gliner2_model_revision,
                chunk_size=settings.gliner2_chunk_size,
                chunk_overlap=settings.gliner2_chunk_overlap,
            )
    return _extractor


def reset_requirement_extractor() -> None:
    """Reset the singleton for tests and controlled process reconfiguration."""

    global _extractor
    with _extractor_factory_lock:
        _extractor = None


__all__ = [
    "Constraint",
    "DEFAULT_GLINER2_MODEL",
    "DEFAULT_GLINER2_REVISION",
    "ExtractionResult",
    "Gliner2RequirementExtractor",
    "Importance",
    "MODEL_LABELS",
    "REQUIREMENT_EXTRACTION_ERROR",
    "REQUIREMENT_EXTRACTOR_VERSION",
    "Requirement",
    "RequirementExtractionError",
    "RequirementExtractor",
    "get_requirement_extractor",
    "requirements_from_model_output",
    "reset_requirement_extractor",
    "to_job_requirements",
]
