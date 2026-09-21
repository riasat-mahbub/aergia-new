"""Section-aware, candidate-facing requirement extraction for the scanner.

The shared GLiNER runtime supplies spans and document chunking. This module
owns eligibility, provenance, requirement normalization, and importance; typed
concept spans alone are never promoted into requirements.
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.scanner.requirements import (
    AllExpression,
    AnyExpression,
    CandidateFacingSignal,
    CandidateSignalKind,
    CandidateSignalPolarity,
    CertificationConstraint,
    Concept,
    DegreeConstraint,
    Expectation,
    ExpectationKind,
    ExpressionModifiers,
    GeographicEligibilityConstraint,
    ImportanceEvidence,
    ImportanceEvidenceKind,
    LanguageProficiencyConstraint,
    MinimumYearsConstraint,
    Requirement,
    RequirementExtraction,
    RequirementFamily,
    RequirementImportance,
    RequirementLeaf,
    RequirementSource,
    SectionContext,
    SectionPurpose,
    WorkAuthorizationConstraint,
)
from app.services.relevance_taxonomy import ALIAS_TO_CANONICAL, TAXONOMY
from app.services.requirement_extractor import (
    MODEL_LABELS,
    RequirementExtractionError,
    get_requirement_extractor,
)

logger = logging.getLogger(__name__)

SCANNER_EXTRACTOR_VERSION = "gliner2.5-structured-v2"
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
_BULLET_RE = re.compile(r"(?m)^[ \t]*[-*•▪‣][ \t]+")
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])[ \t\r\n]+(?=[A-Z0-9])")
_NORMALIZE_RE = re.compile(r"[^\w+#./-]+", re.UNICODE)

_REQUIRED_RE = re.compile(
    r"\b(?:must(?:\s+have|\s+be able to)?|required|mandatory|essential|shall|"
    r"non[- ]negotiable|need to)\b",
    re.IGNORECASE,
)
_NEGATED_REQUIRED_RE = re.compile(
    r"\b(?:not\s+required|not\s+necessary|not\s+mandatory|not\s+(?:a\s+)?requirement|"
    r"not\s+needed)\b",
    re.IGNORECASE,
)
_PREFERRED_RE = re.compile(
    r"\b(?:preferred|preferably|nice\s+to\s+have|good\s+to\s+have|a\s+plus|bonus|"
    r"desirable|advantageous|beneficial|optional|asset)\b",
    re.IGNORECASE,
)
_ELIGIBILITY_RE = re.compile(
    r"\b(?:authorized\s+to\s+work|work\s+authorization|eligible\s+to\s+work|"
    r"right\s+to\s+work|visa\s+sponsorship|must\s+reside|must\s+be\s+located|"
    r"must\s+be\s+based\s+in|reside\s+in)\b",
    re.IGNORECASE,
)
_HARD_BOILERPLATE_RE = re.compile(
    r"\b(?:during\s+our\s+hiring\s+process|initial\s+screening|automated\s+screening|"
    r"human\s+review|accommodation\s+during\s+the\s+application\s+process|"
    r"you(?:['’]ll|\s+will)\s+be\s+supported\s+by|you(?:['’]ll|\s+will)\s+feel\s+safe|"
    r"share\s+your\s+ideas\s+and\s+career\s+goals|promote[- ]from[- ]within|"
    r"equal\s+(?:employment\s+)?opportunity|privacy\s+(?:notice|policy))\b",
    re.IGNORECASE,
)
_COMPANY_COPY_RE = re.compile(
    r"^\s*(?:about\s+(?:us|the\s+company|our\s+team)|we(?:['’]re|\s+are)\s+more\s+than|"
    r"our\s+(?:cloud[- ]based\s+)?platform|we\s+believe\s+in|we\s+celebrate|"
    r"employee[- ]led|founded\s+in|headquartered\s+in|with\s+\d+[+]?\s+employees|"
    r"at\s+[^,.]{2,80},\s+we(?:['’]re|\s+are)\s+more\s+than|"
    r"at\s+[^,.]{2,80},\s+you(?:['’]ll|\s+will)\s+help\s+build\s+technology)\b",
    re.IGNORECASE,
)

_DIRECTED_PATTERNS: tuple[tuple[re.Pattern[str], float], ...] = (
    (re.compile(r"\b(?:you(?:['’]ll|\s+will|\s+must|\s+should|\s+have|\s+are|\s+bring|\s+need|\s+can))\b", re.I), 0.82),
    (re.compile(r"\b(?:familiarity\s+with|experience\s+(?:with|in|of)|knowledge\s+of|"
                r"ability\s+to|able\s+to|proficien(?:t|cy)\s+(?:in|with)|interest\s+in|"
                r"curiosity\s+about|bilingual\s+in|strong\s+\w+\s+skills|"
                r"demonstrated\s+interest|willing\s+to)\b", re.I), 0.82),
    (re.compile(r"^\s*(?:assist|use|pair[- ]program|write|help|participate|learn|design|"
                r"build|develop|test|debug|investigate|maintain|operate|lead|own|"
                r"collaborate|communicate|implement|create)\b", re.I), 0.76),
    (_REQUIRED_RE, 0.90),
)

_EXPECTATION_CUES: tuple[tuple[re.Pattern[str], ExpectationKind, float], ...] = (
    (re.compile(r"\bcuriosity\b", re.I), ExpectationKind.INTEREST, 0.92),
    (re.compile(r"\binterest\b", re.I), ExpectationKind.INTEREST, 0.90),
    (re.compile(r"\bbilingual\b|\bfluent\b", re.I), ExpectationKind.PROFICIENCY, 0.90),
    (re.compile(r"\bfamiliarity\b", re.I), ExpectationKind.FAMILIARITY, 0.92),
    (re.compile(r"\bproficien(?:t|cy)\b", re.I), ExpectationKind.PROFICIENCY, 0.92),
    (re.compile(r"\bexperience\b", re.I), ExpectationKind.PRIOR_EXPERIENCE, 0.90),
    (re.compile(r"\bwilling(?:ness)?\s+to\s+learn\b", re.I), ExpectationKind.WILLINGNESS_TO_LEARN, 0.94),
    (re.compile(r"\blearn\s+and\s+apply\b", re.I), ExpectationKind.DEMONSTRATED_APPLICATION, 0.92),
    (re.compile(r"\bknowledge\b", re.I), ExpectationKind.KNOWLEDGE, 0.88),
    (re.compile(r"\bability\s+to\b|\bable\s+to\b|\bcapable\s+of\b", re.I), ExpectationKind.ABILITY_TO_PERFORM, 0.90),
    (re.compile(r"\b(?:use|using|integrat(?:e|ing))\b", re.I), ExpectationKind.PRACTICAL_USE, 0.84),
    (re.compile(r"\b(?:participate|pair[- ]program|attend)\b", re.I), ExpectationKind.PARTICIPATION, 0.86),
    (re.compile(r"\b(?:write|build|design|develop|test|debug|investigate|maintain|implement|assist|help)\b", re.I), ExpectationKind.ABILITY_TO_PERFORM, 0.78),
    (re.compile(r"\bcommunication\s+skills\b", re.I), ExpectationKind.ABILITY_TO_PERFORM, 0.78),
)

_YEAR_RE = re.compile(
    r"\b(?P<qualifier>at\s+least|minimum(?:\s+of)?|more\s+than|over)?\s*"
    r"(?P<years>\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten)"
    r"\s*(?:\+|or\s+more)?\s+years?\b",
    re.IGNORECASE,
)
_DEGREE_RE = re.compile(
    r"\b(?P<degree>ph\.?d\.?|doctorate|doctoral|master(?:['’]s)?|msc|m\.?s\.?|mba|"
    r"bachelor(?:['’]s)?|bsc|b\.?s\.?|b\.?a\.?|undergraduate|associate(?:['’]s)?)\b",
    re.IGNORECASE,
)
_LANGUAGE_RE = re.compile(r"\b(?:bilingual|fluent|proficient|native|conversational)\b", re.I)
_LANGUAGE_NAMES = {"english", "french", "spanish", "german", "portuguese", "mandarin", "chinese", "arabic", "japanese"}
_CUSTOM_TERMS: tuple[tuple[str, str, str], ...] = (
    ("implementing with ai", "AI-assisted development", "technical_skill"),
    ("ai-assisted development", "AI-assisted development", "technical_skill"),
    ("ai tools", "AI tools", "technical_skill"),
    ("genai", "GenAI", "technical_skill"),
    ("ai", "AI-assisted development", "technical_skill"),
    ("containerization", "containerization", "technical_skill"),
    ("containerisation", "containerization", "technical_skill"),
    ("monitoring", "monitoring", "technical_skill"),
    ("automated tests", "automated testing", "technical_skill"),
    ("automated testing", "automated testing", "technical_skill"),
    ("pair-programming", "pair programming", "responsibility"),
    ("pair-program", "pair programming", "responsibility"),
    ("standups", "standups", "responsibility"),
    ("demos", "demos", "responsibility"),
    ("retrospectives", "retrospectives", "responsibility"),
    ("full-stack developer", "full-stack development", "responsibility"),
    ("full stack developer", "full-stack development", "responsibility"),
    ("front-end", "front-end development", "responsibility"),
    ("back-end", "back-end development", "responsibility"),
    ("industry trends", "industry trends", "behavioral"),
    ("technology", "technology", "technical_skill"),
    ("performance", "software performance", "technical_skill"),
    ("english", "English", "language"),
    ("french", "French", "language"),
    ("spanish", "Spanish", "language"),
    ("german", "German", "language"),
    ("portuguese", "Portuguese", "language"),
    ("mandarin", "Mandarin", "language"),
    ("chinese", "Chinese", "language"),
    ("arabic", "Arabic", "language"),
    ("japanese", "Japanese", "language"),
)
_ACTION_LIST_RE = re.compile(r"\b(?:assist\s+in|help)\s+(?P<actions>[^.;]+?)\s+(?P<object>software\s+features?|bugs?|issues?)\b", re.I)
_ACTION_WORD_RE = re.compile(r"\b(?:design(?:ing)?|cod(?:e|ing)|test(?:ing)?|debug(?:ging)?|investigat(?:e|ing)|reproduc(?:e|ing)|resolv(?:e|ing))\b", re.I)
_ACTION_NAMES = {
    "design": "software feature design",
    "designing": "software feature design",
    "code": "software feature implementation",
    "coding": "software feature implementation",
    "test": "software feature testing",
    "testing": "software feature testing",
    "debug": "software feature debugging",
    "debugging": "software feature debugging",
    "investigate": "bug investigation",
    "investigating": "bug investigation",
    "reproduce": "bug reproduction",
    "reproducing": "bug reproduction",
    "resolve": "bug resolution",
    "resolving": "bug resolution",
}


class EntityModel(Protocol):
    def extract_entities(self, text: str, labels: Mapping[str, str], **kwargs: Any) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class _EntitySpan:
    label: str
    text: str
    start: int | None
    end: int | None
    confidence: float


@dataclass(frozen=True, slots=True)
class _Section:
    title: str | None
    purpose: SectionPurpose
    confidence: float
    heading_start: int | None
    content_start: int
    end: int


@dataclass(frozen=True, slots=True)
class _Sentence:
    text: str
    start: int
    end: int
    section: _Section


@dataclass(frozen=True, slots=True)
class CandidateTextSegment:
    """A candidate-facing source span used by independent scanner branches."""

    text: str
    source_start: int
    source_end: int
    section_title: str | None
    section_purpose: SectionPurpose
    section_confidence: float


@dataclass(frozen=True, slots=True)
class _Component:
    concept: Concept
    start: int
    end: int
    label: str


def _normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _heading_text(value: str) -> str:
    return value.strip().strip("# ").strip(" -*•▪‣\t").rstrip(":").strip()


def _purpose_for_heading(value: str | None) -> tuple[SectionPurpose, float]:
    if not value:
        return SectionPurpose.UNKNOWN, 0.35
    normalized = re.sub(r"[^\w]+", " ", _normalize(value)).strip()
    normalized = normalized.replace(" you ll ", " youll ").replace(" you re ", " youre ")
    if normalized in {"what youll do", "responsibilities", "key responsibilities", "your responsibilities", "what you will do", "duties", "about the role"}:
        return SectionPurpose.CANDIDATE_RESPONSIBILITIES, 0.82 if normalized != "about the role" else 0.62
    if normalized in {"what you bring", "what you bring to the team", "qualifications", "requirements", "candidate requirements", "minimum qualifications", "required qualifications", "skills", "experience", "candidate profile", "your profile", "who you are"}:
        return SectionPurpose.CANDIDATE_QUALIFICATIONS, 0.84
    if normalized in {"preferred qualifications", "preferred skills", "nice to have", "nice to haves", "bonus qualifications", "desired qualifications", "preferred requirements"}:
        return SectionPurpose.CANDIDATE_PREFERENCES, 0.88
    if normalized in {"benefits", "benefits and perks", "perks", "compensation", "salary", "total rewards"}:
        return SectionPurpose.BENEFITS, 0.90
    if normalized in {"location", "locations", "location and work model", "work model", "work arrangement", "remote work", "where you work"}:
        return SectionPurpose.LOGISTICS, 0.90
    if normalized in {"application process", "how to apply", "ready to join us", "apply", "application"}:
        return SectionPurpose.APPLICATION_PROCESS, 0.88
    if normalized in {"legal", "equal opportunity", "equal employment opportunity", "privacy", "accessibility", "accommodation"}:
        return SectionPurpose.LEGAL, 0.88
    if normalized.startswith(("about ", "why join", "work with purpose", "grow in a", "inclusive by design", "our mission", "our values", "who we are", "company overview", "company description")):
        return SectionPurpose.EMPLOYER_INFORMATION, 0.88
    return SectionPurpose.UNKNOWN, 0.45


def _is_heading(line: str) -> bool:
    title = _heading_text(line)
    if not title:
        return False
    purpose, confidence = _purpose_for_heading(title)
    if purpose is not SectionPurpose.UNKNOWN and confidence >= 0.6:
        return True
    if line.rstrip().endswith(":") and len(title.split()) <= 12:
        return True
    if re.search(r"[.!?]", title) or len(title.split()) > 7:
        return False
    words = [word for word in title.split() if word[:1].isalpha()]
    return bool(words) and sum(word[:1].isupper() for word in words) / len(words) >= 0.8


def _sections(source: str) -> list[_Section]:
    headings: list[tuple[int, int, str, SectionPurpose, float]] = []
    for match in re.finditer(r"[^\n]+", source):
        if not _is_heading(match.group(0)):
            continue
        title = _heading_text(match.group(0))
        purpose, confidence = _purpose_for_heading(title)
        headings.append((match.start(), match.end(), title, purpose, confidence))

    if not headings:
        return [_Section(None, SectionPurpose.UNKNOWN, 0.35, None, 0, len(source))]

    sections: list[_Section] = []
    if headings[0][0] > 0 and source[: headings[0][0]].strip():
        sections.append(_Section(None, SectionPurpose.UNKNOWN, 0.35, None, 0, headings[0][0]))
    for index, (heading_start, heading_end, title, purpose, confidence) in enumerate(headings):
        content_start = heading_end
        while content_start < len(source) and source[content_start] in "\r\n":
            content_start += 1
        end = headings[index + 1][0] if index + 1 < len(headings) else len(source)
        sections.append(_Section(title, purpose, confidence, heading_start, content_start, end))
    return sections


def _trimmed_range(source: str, start: int, end: int, *, strip_bullet: bool = True) -> tuple[int, int]:
    while start < end and source[start].isspace():
        start += 1
    if strip_bullet and start < end and source[start] in "-*•▪‣":
        start += 1
        while start < end and source[start].isspace():
            start += 1
    while end > start and source[end - 1].isspace():
        end -= 1
    return start, end


def _sentence_ranges(source: str, section: _Section) -> list[_Sentence]:
    bullets = [match.start() for match in _BULLET_RE.finditer(source, section.content_start, section.end)]
    block_boundaries = [section.content_start]
    block_boundaries.extend(position for position in bullets if position > section.content_start)
    block_boundaries.append(section.end)
    sentences: list[_Sentence] = []
    for block_start, block_end in zip(block_boundaries, block_boundaries[1:], strict=False):
        block = source[block_start:block_end]
        cursor = 0
        for boundary in _SENTENCE_BOUNDARY_RE.finditer(block):
            start, end = _trimmed_range(source, block_start + cursor, block_start + boundary.start())
            if start < end:
                sentences.append(_Sentence(source[start:end], start, end, section))
            cursor = boundary.end()
        start, end = _trimmed_range(source, block_start + cursor, block_end)
        if start < end:
            sentences.append(_Sentence(source[start:end], start, end, section))
    return sentences


def _all_sentences(source: str) -> list[_Sentence]:
    result: list[_Sentence] = []
    for section in _sections(source):
        result.extend(_sentence_ranges(source, section))
    return result


def _coerce_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _find_span(source: str, value: str, cursor: int = 0) -> tuple[int | None, int | None]:
    start = source.find(value, cursor)
    if start < 0:
        folded_source = source.casefold()
        start = folded_source.find(value.casefold(), cursor)
    if start < 0:
        return None, None
    return start, start + len(value)


def _coerce_spans(source: str, raw: Mapping[str, Any] | Sequence[Any]) -> list[_EntitySpan]:
    if isinstance(raw, Mapping):
        entities = raw.get("entities", raw)
        if not isinstance(entities, Mapping):
            return []
        spans: list[_EntitySpan] = []
        for label, values in entities.items():
            if isinstance(values, (str, Mapping)):
                values = [values]
            if not isinstance(values, Sequence):
                continue
            cursor = 0
            for value in values:
                if isinstance(value, Mapping):
                    text = value.get("text")
                    start = value.get("start")
                    end = value.get("end")
                    confidence = value.get("confidence", value.get("score", 0.0))
                else:
                    text = value
                    start = end = None
                    confidence = 0.0
                if not isinstance(text, str) or not text.strip():
                    continue
                try:
                    start, end = int(start), int(end)
                except (TypeError, ValueError):
                    start = end = -1
                if start < 0 or end <= start or end > len(source) or _normalize(source[start:end]) != _normalize(text):
                    found_start, found_end = _find_span(source, text, cursor)
                    start, end = found_start if found_start is not None else -1, found_end if found_end is not None else -1
                if start >= 0 and end > start:
                    cursor = end
                    text = source[start:end]
                spans.append(
                    _EntitySpan(
                        label=str(label).casefold().replace("-", "_"),
                        text=text.strip(),
                        start=start if start >= 0 else None,
                        end=end if end > start else None,
                        confidence=_coerce_confidence(confidence),
                    )
                )
        return spans

    spans = []
    for raw_span in raw:
        label = getattr(raw_span, "label", None)
        text = getattr(raw_span, "text", None)
        start = getattr(raw_span, "start", None)
        end = getattr(raw_span, "end", None)
        confidence = getattr(raw_span, "confidence", 0.0)
        if not isinstance(label, str) or not isinstance(text, str):
            continue
        if start is not None and end is not None:
            try:
                start, end = int(start), int(end)
            except (TypeError, ValueError):
                start = end = None
        spans.append(_EntitySpan(label.casefold().replace("-", "_"), text, start, end, _coerce_confidence(confidence)))
    return spans


def _overlaps(span: _EntitySpan, sentence: _Sentence) -> bool:
    return span.start is not None and span.end is not None and max(0, min(span.end, sentence.end) - max(span.start, sentence.start)) > 0


def _directed_signal(text: str) -> tuple[str, float] | None:
    for pattern, confidence in _DIRECTED_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0), confidence
    return None


def _is_hard_non_candidate(sentence: _Sentence) -> bool:
    return bool(
        _HARD_BOILERPLATE_RE.search(sentence.text)
        or _COMPANY_COPY_RE.search(sentence.text)
    )


def _candidate_eligibility(sentence: _Sentence, spans: Sequence[_EntitySpan]) -> tuple[bool, float, list[CandidateFacingSignal]]:
    purpose = sentence.section.purpose
    explicit = [span for span in spans if span.label in _REQUIREMENT_LABELS and _overlaps(span, sentence)]
    directed = _directed_signal(sentence.text)
    eligibility_language = _ELIGIBILITY_RE.search(sentence.text)
    hard_non_candidate = _is_hard_non_candidate(sentence)

    # Hiring, legal, and company boilerplate is excluded by sentence content;
    # a section label by itself is only one contextual signal.
    if hard_non_candidate:
        return False, max(sentence.section.confidence, 0.9), [
            CandidateFacingSignal(
                kind=CandidateSignalKind.SECTION_CONTEXT,
                polarity=CandidateSignalPolarity.OPPOSES,
                confidence=max(sentence.section.confidence, 0.9),
                source_text=sentence.section.title or sentence.text[:160],
            )
        ]

    signals: list[CandidateFacingSignal] = []
    positive_scores: list[float] = []
    for span in explicit:
        positive_scores.append(max(0.58, span.confidence))
        signals.append(
            CandidateFacingSignal(
                kind=CandidateSignalKind.REQUIREMENT_MODEL_SPAN,
                polarity=CandidateSignalPolarity.SUPPORTS,
                confidence=max(0.58, span.confidence),
                source_text=span.text,
            )
        )
    if directed:
        signal_text, confidence = directed
        positive_scores.append(confidence)
        signals.append(
            CandidateFacingSignal(
                kind=CandidateSignalKind.CANDIDATE_DIRECTED_LANGUAGE,
                polarity=CandidateSignalPolarity.SUPPORTS,
                confidence=confidence,
                source_text=signal_text,
            )
        )
    if purpose in {
        SectionPurpose.CANDIDATE_RESPONSIBILITIES,
        SectionPurpose.CANDIDATE_QUALIFICATIONS,
        SectionPurpose.CANDIDATE_PREFERENCES,
    }:
        positive_scores.append(sentence.section.confidence * 0.65)
        signals.append(
            CandidateFacingSignal(
                kind=CandidateSignalKind.SECTION_CONTEXT,
                polarity=CandidateSignalPolarity.SUPPORTS,
                confidence=sentence.section.confidence,
                source_text=sentence.section.title or "candidate-facing section",
            )
        )

        # A typed skill/responsibility span is useful together with a known
        # candidate-facing section, but must not admit a sentence by itself.
        concept_spans = [
            span
            for span in spans
            if span.label in _CONCEPT_LABELS and _overlaps(span, sentence)
        ]
        for span in concept_spans:
            concept_score = max(0.25, min(0.45, span.confidence * 0.45))
            positive_scores.append(concept_score)
            signals.append(
                CandidateFacingSignal(
                    kind=CandidateSignalKind.CONCEPT_IN_CANDIDATE_SECTION,
                    polarity=CandidateSignalPolarity.SUPPORTS,
                    confidence=concept_score,
                    source_text=span.text,
                )
            )

    if purpose in {
        SectionPurpose.EMPLOYER_INFORMATION,
        SectionPurpose.BENEFITS,
        SectionPurpose.LOGISTICS,
        SectionPurpose.APPLICATION_PROCESS,
        SectionPurpose.LEGAL,
    } and not eligibility_language:
        opposition = sentence.section.confidence * 0.20
        signals.append(
            CandidateFacingSignal(
                kind=CandidateSignalKind.SECTION_CONTEXT,
                polarity=CandidateSignalPolarity.OPPOSES,
                confidence=sentence.section.confidence,
                source_text=sentence.section.title or "non-candidate section",
            )
        )
    else:
        opposition = 0.0

    if not positive_scores:
        return False, max(0.0, opposition), signals
    combined = 1.0
    for score in positive_scores:
        combined *= 1.0 - min(1.0, score)
    combined = 1.0 - combined
    confidence = max(0.0, min(1.0, combined - opposition))
    # A location/work-authorization statement is a separate eligibility fact,
    # even when it appears under logistics or legal headings.
    if eligibility_language:
        signals.append(
            CandidateFacingSignal(
                kind=CandidateSignalKind.SENTENCE_CLASSIFIER,
                polarity=CandidateSignalPolarity.SUPPORTS,
                confidence=0.88,
                source_text=eligibility_language.group(0),
            )
        )
        confidence = max(confidence, 0.75)
    return confidence >= 0.58, confidence, signals


def candidate_facing_segments(source: str) -> list[CandidateTextSegment]:
    """Return candidate-facing text spans without consulting semantic output.

    This is deliberately an independent, deterministic path for lexical term
    inventory. It shares section/sentence boundaries and boilerplate rules,
    but it does not consume requirement extraction results or GLiNER concepts.
    """

    segments: list[CandidateTextSegment] = []
    for sentence in _all_sentences(source):
        eligible, _confidence, _signals = _candidate_eligibility(sentence, ())
        if (
            not eligible
            and sentence.section.purpose
            in {
                SectionPurpose.CANDIDATE_RESPONSIBILITIES,
                SectionPurpose.CANDIDATE_QUALIFICATIONS,
                SectionPurpose.CANDIDATE_PREFERENCES,
            }
            and not _is_hard_non_candidate(sentence)
        ):
            # The lexical inventory needs candidate-section text even when a
            # sentence has no requirement verb or semantic requirement span.
            eligible = True
        if not eligible:
            continue
        segments.append(
            CandidateTextSegment(
                text=sentence.text,
                source_start=sentence.start,
                source_end=sentence.end,
                section_title=sentence.section.title,
                section_purpose=sentence.section.purpose,
                section_confidence=sentence.section.confidence,
            )
        )
    return segments


def _taxonomy_components(text: str, base: int) -> list[_Component]:
    folded = text.casefold()
    matches: list[tuple[int, int, str]] = []
    for alias, canonical in sorted(ALIAS_TO_CANONICAL.items(), key=lambda item: (-len(item[0]), item[0])):
        for match in re.finditer(rf"(?<![\w]){re.escape(alias.casefold())}(?![\w])", folded):
            matches.append((match.start(), match.end(), canonical))
    matches.sort(key=lambda item: (item[0], -(item[1] - item[0]), item[2]))
    selected: list[tuple[int, int, str]] = []
    canonical_seen: set[str] = set()
    for match in matches:
        start, end, canonical = match
        if canonical in canonical_seen:
            continue
        if any(start < existing_end and end > existing_start for existing_start, existing_end, _ in selected):
            continue
        selected.append(match)
        canonical_seen.add(canonical)

    components: list[_Component] = []
    for start, end, canonical in selected:
        family = TAXONOMY.get(canonical, ("other", ()))[0]
        components.append(
            _Component(
                concept=Concept(
                    name=canonical,
                    canonical_id=canonical,
                    family=family,
                    source_text=text[start:end],
                    confidence=0.68,
                ),
                start=base + start,
                end=base + end,
                label=family,
            )
        )
    return components


def _custom_components(text: str, base: int, *, ignore_before: int = 0) -> list[_Component]:
    matches: list[tuple[int, int, str, str]] = []
    folded = text.casefold()
    for alias, canonical, family in sorted(_CUSTOM_TERMS, key=lambda item: (-len(item[0]), item[0])):
        for match in re.finditer(rf"(?<![\w]){re.escape(alias.casefold())}(?![\w])", folded):
            if match.start() >= ignore_before:
                matches.append((match.start(), match.end(), canonical, family))
    matches.sort(key=lambda item: (item[0], -(item[1] - item[0]), item[2]))
    selected: list[tuple[int, int, str, str]] = []
    names: set[str] = set()
    for item in matches:
        start, end, name, _family = item
        if _normalize(name) in names:
            continue
        if any(start < previous_end and end > previous_start for previous_start, previous_end, _, _ in selected):
            continue
        selected.append(item)
        names.add(_normalize(name))
    return [
        _Component(
            concept=Concept(
                name=name,
                canonical_id=f"scanner:{_normalize(name).replace(' ', '_')}",
                family=family,
                source_text=text[start:end],
                confidence=0.72,
            ),
            start=base + start,
            end=base + end,
            label="bounded_lexicon",
        )
        for start, end, name, family in selected
    ]


def _action_components(sentence: _Sentence, *, ignore_before: int = 0) -> list[_Component]:
    action_list = _ACTION_LIST_RE.search(sentence.text)
    if not action_list:
        return []
    region_start = action_list.start("actions")
    components: list[_Component] = []
    for match in _ACTION_WORD_RE.finditer(action_list.group("actions")):
        local_start = region_start + match.start()
        local_end = region_start + match.end()
        if local_start < ignore_before:
            continue
        action = match.group(0).casefold()
        name = _ACTION_NAMES[action]
        object_name = "software features" if "software feature" in name else "bugs"
        components.append(
            _Component(
                concept=Concept(
                    name=name,
                    canonical_id=f"scanner:{name.replace(' ', '_')}",
                    family="responsibility",
                    source_text=f"{match.group(0)} {object_name}",
                    confidence=0.72,
                ),
                start=sentence.start + local_start,
                end=sentence.start + local_end,
                label="action_component",
            )
        )
    return components


def _components_for(sentence: _Sentence, spans: Sequence[_EntitySpan]) -> list[_Component]:
    role_preface = re.match(r"\s*as\s+(?:a|an)\s+[^,]{1,120},", sentence.text, re.I)
    ignore_before = role_preface.end() if role_preface else 0
    typed = [
        span
        for span in spans
        if span.label in _CONCEPT_LABELS
        and _overlaps(span, sentence)
        and span.start is not None
        and span.end is not None
        and max(span.start, sentence.start) >= sentence.start + ignore_before
    ]
    named = [
        *[item for item in _taxonomy_components(sentence.text, sentence.start) if item.start >= sentence.start + ignore_before],
        *_custom_components(sentence.text, sentence.start, ignore_before=ignore_before),
    ]
    components = _action_components(sentence, ignore_before=ignore_before)
    for span in typed:
        local_start = max(span.start or sentence.start, sentence.start)
        local_end = min(span.end or sentence.end, sentence.end)
        raw_text = sentence.text[local_start - sentence.start : local_end - sentence.start]
        nested_matches = [item for item in named if local_start <= item.start and item.end <= local_end]
        if len(nested_matches) > 1 or (local_end - local_start) / max(1, sentence.end - sentence.start) > 0.72 and named:
            continue
        if any(local_start < item.end and local_end > item.start for item in components):
            continue
        canonical = ALIAS_TO_CANONICAL.get(_normalize(raw_text))
        if canonical and canonical in TAXONOMY:
            name = canonical
            family = TAXONOMY[canonical][0]
        else:
            name = raw_text.strip()
            family = {
                "hard_skill": "technical_skill",
                "experience_requirement": "experience",
                "education_requirement": "education",
                "certification_requirement": "certification",
                "responsibility": "responsibility",
                "quantitative_constraint": "experience",
                "domain_knowledge": "other",
            }.get(span.label, "other")
        if any(_normalize(item.concept.name) == _normalize(name) for item in components):
            continue
        components.append(
            _Component(
                concept=Concept(
                    name=name,
                    canonical_id=canonical,
                    family=family,
                    source_text=raw_text,
                    confidence=max(0.0, min(1.0, span.confidence)),
                ),
                start=local_start,
                end=local_end,
                label=span.label,
            )
        )
    for item in named:
        if not any(
            _normalize(existing.concept.name) == _normalize(item.concept.name)
            or item.start < existing.end and item.end > existing.start
            for existing in components
        ):
            components.append(item)
    degree = _DEGREE_RE.search(sentence.text)
    if degree and not any(item.concept.family == "education" for item in components):
        components.append(
            _Component(
                concept=Concept(
                    name="education degree",
                    canonical_id="scanner:education_degree",
                    family="education",
                    source_text=degree.group(0),
                    confidence=0.76,
                ),
                start=sentence.start + degree.start(),
                end=sentence.start + degree.end(),
                label="derived_degree",
            )
        )
    components.sort(key=lambda item: (item.start, item.end, item.concept.name.casefold()))
    if not components:
        family = (
            "eligibility"
            if _ELIGIBILITY_RE.search(sentence.text)
            else "behavioral"
            if re.search(r"\b(?:communication|collaborat|curiosity|interest)\b", sentence.text, re.I)
            else "other"
        )
        fallback_start = min(ignore_before, max(0, len(sentence.text) - 1))
        fallback_text = sentence.text[fallback_start:].strip() or sentence.text
        components.append(
            _Component(
                concept=Concept(
                    name=fallback_text,
                    family=family,
                    source_text=fallback_text,
                    confidence=0.38,
                ),
                start=sentence.start + fallback_start,
                end=sentence.end,
                label="derived_source_phrase",
            )
        )
    return components


def _expectation_for(sentence: _Sentence, component: _Component) -> Expectation:
    relative_start = max(0, component.start - sentence.start)
    cues: list[tuple[int, int, ExpectationKind, float, str]] = []
    for pattern, kind, confidence in _EXPECTATION_CUES:
        for match in pattern.finditer(sentence.text):
            cues.append((match.start(), match.end(), kind, confidence, match.group(0)))
    if cues:
        cue = min(cues, key=lambda item: min(abs(relative_start - item[0]), abs(relative_start - item[1])))
        qualifier = sentence.text[max(0, cue[0] - 24) : min(len(sentence.text), cue[1] + 64)].strip()
        return Expectation(kind=cue[2], qualifier=qualifier[:500], source_text=cue[4], confidence=cue[3])
    if component.concept.family == "responsibility":
        return Expectation(
            kind=ExpectationKind.ABILITY_TO_PERFORM,
            source_text=sentence.text,
            confidence=0.58,
        )
    return Expectation(kind=ExpectationKind.OTHER, source_text=sentence.text, confidence=0.35)


def _constraint_for(sentence: _Sentence, component: _Component, node_id: str) -> list[Any]:
    constraints: list[Any] = []
    years = _YEAR_RE.search(sentence.text)
    if years and component.concept.family in {"hard_skill", "technical_skill", "experience", "responsibility", "other"}:
        numbers = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
        raw_years = years.group("years").casefold()
        qualifier = (years.group("qualifier") or "").casefold()
        constraints.append(
            MinimumYearsConstraint(
                id=f"{node_id}-years",
                kind="minimum_years",
                years=float(numbers.get(raw_years, raw_years)),
                operator="gt" if qualifier in {"more than", "over"} else "gte",
                source_text=sentence.text[years.start() : years.end()].strip(),
                confidence=0.90,
            )
        )
    degree = _DEGREE_RE.search(sentence.text)
    if degree and component.concept.family == "education":
        raw_degree = degree.group("degree").casefold().replace("’", "'").replace(".", "")
        level = "doctorate" if "ph" in raw_degree or "doctor" in raw_degree else "master" if any(word in raw_degree for word in ("master", "msc", "ms", "mba")) else "bachelor" if any(word in raw_degree for word in ("bachelor", "bsc", "bs", "ba", "undergraduate")) else "associate"
        constraints.append(
            DegreeConstraint(
                id=f"{node_id}-degree",
                kind="degree",
                level=level,
                source_text=degree.group(0),
                confidence=0.90,
            )
        )
    if component.concept.family == "certification":
        constraints.append(
            CertificationConstraint(
                id=f"{node_id}-certification",
                kind="certification",
                name=component.concept.name,
                source_text=component.concept.source_text or component.concept.name,
                confidence=component.concept.confidence,
            )
        )
    if component.concept.name.casefold() in _LANGUAGE_NAMES and _LANGUAGE_RE.search(sentence.text):
        language_cue = _LANGUAGE_RE.search(sentence.text)
        constraints.append(
            LanguageProficiencyConstraint(
                id=f"{node_id}-language",
                kind="language_proficiency",
                language=component.concept.name,
                level=language_cue.group(0).casefold() if language_cue else None,
                source_text=language_cue.group(0) if language_cue else sentence.text,
                confidence=0.88,
            )
        )
    if component.concept.family == "eligibility" and re.search(r"\b(?:authorized|eligible|right)\s+to\s+work\b", sentence.text, re.I):
        constraints.append(
            WorkAuthorizationConstraint(
                id=f"{node_id}-authorization",
                kind="work_authorization",
                jurisdiction=None,
                source_text=sentence.text,
                confidence=0.88,
            )
        )
    location = re.search(
        r"\b(?:must\s+be\s+located\s+in|must\s+be\s+based\s+in|must\s+reside\s+in|reside\s+in)\s+(?P<place>[^,.;]+)",
        sentence.text,
        re.I,
    )
    if component.concept.family == "eligibility" and location:
        constraints.append(
            GeographicEligibilityConstraint(
                id=f"{node_id}-location",
                kind="geographic_eligibility",
                locations=[location.group("place").strip()],
                relation="all",
                source_text=location.group(0),
                confidence=0.84,
            )
        )
    return constraints


def _importance(sentence: _Sentence, spans: Sequence[_EntitySpan]) -> tuple[RequirementImportance, float, list[ImportanceEvidence]]:
    text = sentence.text
    evidence: list[ImportanceEvidence] = []
    negated = _NEGATED_REQUIRED_RE.search(text)
    required = _REQUIRED_RE.search(text)
    preferred = _PREFERRED_RE.search(text)
    model_preferred = [span for span in spans if span.label == "preferred_requirement" and _overlaps(span, sentence)]

    if negated:
        evidence.append(ImportanceEvidence(kind=ImportanceEvidenceKind.NEGATED, interpretation=RequirementImportance.UNKNOWN, source_text=negated.group(0), confidence=0.92))
        return RequirementImportance.UNKNOWN, 0.92, evidence
    if (preferred or model_preferred) and required:
        evidence.extend(
            [
                ImportanceEvidence(
                    kind=ImportanceEvidenceKind.EXPLICIT_PREFERRED if preferred else ImportanceEvidenceKind.MODEL_LABEL,
                    interpretation=RequirementImportance.PREFERRED,
                    source_text=(preferred.group(0) if preferred else model_preferred[0].text)[:500],
                    confidence=0.88 if preferred else model_preferred[0].confidence,
                ),
                ImportanceEvidence(kind=ImportanceEvidenceKind.EXPLICIT_REQUIRED, interpretation=RequirementImportance.REQUIRED, source_text=required.group(0), confidence=0.88),
            ]
        )
        return RequirementImportance.UNKNOWN, 0.70, evidence
    if preferred or model_preferred:
        source_text = preferred.group(0) if preferred else model_preferred[0].text
        evidence.append(ImportanceEvidence(kind=ImportanceEvidenceKind.EXPLICIT_PREFERRED if preferred else ImportanceEvidenceKind.MODEL_LABEL, interpretation=RequirementImportance.PREFERRED, source_text=source_text[:500], confidence=0.94 if preferred else model_preferred[0].confidence))
        return RequirementImportance.PREFERRED, evidence[-1].confidence, evidence
    if required:
        evidence.append(ImportanceEvidence(kind=ImportanceEvidenceKind.EXPLICIT_REQUIRED, interpretation=RequirementImportance.REQUIRED, source_text=required.group(0), confidence=0.94))
        return RequirementImportance.REQUIRED, 0.94, evidence
    if sentence.section.purpose is SectionPurpose.CANDIDATE_PREFERENCES:
        evidence.append(ImportanceEvidence(kind=ImportanceEvidenceKind.SECTION_CONTEXT, interpretation=RequirementImportance.PREFERRED, source_text=sentence.section.title or "preferred section", confidence=sentence.section.confidence))
        return RequirementImportance.PREFERRED, sentence.section.confidence, evidence
    if sentence.section.purpose in {SectionPurpose.CANDIDATE_RESPONSIBILITIES, SectionPurpose.CANDIDATE_QUALIFICATIONS}:
        evidence.append(ImportanceEvidence(kind=ImportanceEvidenceKind.SECTION_CONTEXT, interpretation=RequirementImportance.REQUIRED, source_text=sentence.section.title or "candidate-facing section", confidence=sentence.section.confidence))
        return RequirementImportance.REQUIRED, sentence.section.confidence * 0.70, evidence
    return RequirementImportance.UNKNOWN, 0.45, evidence


def _relation_tree(
    sentence: _Sentence,
    components: Sequence[_Component],
    leaves: Sequence[RequirementLeaf],
    requirement_id: str,
    confidence: float,
) -> Any:
    if len(leaves) == 1:
        return leaves[0]
    connectors: list[str] = []
    for left, right in zip(components, components[1:], strict=False):
        gap = sentence.text[max(0, left.end - sentence.start) : max(0, right.start - sentence.start)]
        if re.search(r"\bor\b", gap, re.I):
            connectors.append("or")
        elif re.search(r"\band\b", gap, re.I):
            connectors.append("and")
        else:
            connectors.append("comma")

    explicit_one_of = bool(re.search(r"\b(?:at\s+least\s+one|one\s+of|either)\b", sentence.text, re.I))
    examples = bool(
        re.search(r"\b(?:e\.g\.|such as|for example|or similar)\b", sentence.text, re.I)
        and not re.search(r"\bincluding\b", sentence.text, re.I)
    )
    if explicit_one_of or examples:
        return AnyExpression(
            kind="any",
            id=f"{requirement_id}-any",
            children=list(leaves),
            modifiers=ExpressionModifiers(list_semantics="examples" if examples else "unknown"),
            confidence=confidence,
        )

    groups: list[list[RequirementLeaf]] = []
    current: list[RequirementLeaf] = [leaves[0]]
    for index, connector in enumerate(connectors):
        next_leaf = leaves[index + 1]
        if connector == "and":
            groups.append(current)
            current = [next_leaf]
        else:
            current.append(next_leaf)
    groups.append(current)

    grouped: list[Any] = []
    for index, group in enumerate(groups):
        start_index = sum(len(item) for item in groups[:index])
        group_connectors = connectors[start_index : start_index + max(0, len(group) - 1)]
        if len(group) == 1:
            grouped.append(group[0])
        elif "or" in group_connectors:
            grouped.append(
                AnyExpression(
                    kind="any",
                    id=f"{requirement_id}-any-{index + 1}",
                    children=group,
                    modifiers=ExpressionModifiers(list_semantics="examples" if examples else "unknown"),
                    confidence=confidence,
                )
            )
        else:
            grouped.append(
                AllExpression(
                    kind="all",
                    id=f"{requirement_id}-all-{index + 1}",
                    children=group,
                    modifiers=ExpressionModifiers(list_semantics="exhaustive" if re.search(r"\bincluding\b", sentence.text, re.I) else "unknown"),
                    confidence=confidence,
                )
            )
    if len(grouped) == 1:
        return grouped[0]
    return AllExpression(
        kind="all",
        id=f"{requirement_id}-all",
        children=grouped,
        modifiers=ExpressionModifiers(list_semantics="exhaustive" if re.search(r"\bincluding\b", sentence.text, re.I) else "unknown"),
        confidence=confidence,
    )


def _requirement_family(sentence: _Sentence, components: Sequence[_Component]) -> RequirementFamily:
    if re.search(r"\b(?:bilingual|language proficiency|fluent in)\b", sentence.text, re.I):
        return RequirementFamily.LANGUAGE
    if re.search(r"\b(?:authorized to work|work authorization|eligible to work|must reside|must be located|must be based in)\b", sentence.text, re.I):
        return RequirementFamily.ELIGIBILITY
    if _YEAR_RE.search(sentence.text):
        return RequirementFamily.EXPERIENCE
    if _DEGREE_RE.search(sentence.text):
        return RequirementFamily.EDUCATION
    families = {item.concept.family for item in components}
    if "certification" in families:
        return RequirementFamily.CERTIFICATION
    if "education" in families:
        return RequirementFamily.EDUCATION
    if "experience" in families:
        return RequirementFamily.EXPERIENCE
    if "technical_skill" in families or "hard_skill" in families:
        return RequirementFamily.TECHNICAL_SKILL
    if "behavioral" in families or any(word in sentence.text.casefold() for word in ("communication", "collaborat", "curiosity", "interest")):
        return RequirementFamily.BEHAVIORAL
    if sentence.section.purpose is SectionPurpose.CANDIDATE_RESPONSIBILITIES:
        return RequirementFamily.RESPONSIBILITY
    if "responsibility" in families:
        return RequirementFamily.RESPONSIBILITY
    return RequirementFamily.OTHER


def _build_requirement(sentence: _Sentence, spans: Sequence[_EntitySpan], index: int, version: str, confidence: float, signals: list[CandidateFacingSignal]) -> Requirement:
    requirement_id = f"req-{index:03d}"
    components = _components_for(sentence, spans)
    leaves: list[RequirementLeaf] = []
    for leaf_index, component in enumerate(components, start=1):
        node_id = f"{requirement_id}-component-{leaf_index:02d}"
        expectation = _expectation_for(sentence, component)
        leaves.append(
            RequirementLeaf(
                kind="leaf",
                id=node_id,
                concept=component.concept,
                expectation=expectation,
                constraints=_constraint_for(sentence, component, node_id),
                modifiers=ExpressionModifiers(
                    optional=bool(re.search(r"\b(?:optional(?:ly)?|optionally)\b", sentence.text[max(0, component.start - sentence.start - 32) : min(len(sentence.text), component.end - sentence.start + 48)], re.I))
                ),
                confidence=min(confidence, component.concept.confidence),
            )
        )
    expression = _relation_tree(sentence, components, leaves, requirement_id, confidence)
    importance, importance_confidence, importance_evidence = _importance(sentence, spans)
    section_start = sentence.section.heading_start if sentence.section.heading_start is not None else sentence.section.content_start
    section = SectionContext(
        title=sentence.section.title,
        purpose=sentence.section.purpose,
        confidence=sentence.section.confidence,
        source_start=section_start,
        source_end=max(section_start + 1, sentence.section.end),
    )
    source = RequirementSource(
        original_text=sentence.text,
        source_start=sentence.start,
        source_end=sentence.end,
        section=section,
        candidate_signals=signals,
        extraction_confidence=confidence,
        extractor_version=version,
    )
    return Requirement(
        id=requirement_id,
        source=source,
        importance=importance,
        importance_confidence=importance_confidence,
        importance_evidence=importance_evidence,
        family=_requirement_family(sentence, components),
        weight=1.0,
        expression=expression,
    )


def extract_requirements_from_entities(
    job_description: str,
    model_output: Mapping[str, Any] | Sequence[Any],
    *,
    extractor_version: str = SCANNER_EXTRACTOR_VERSION,
) -> RequirementExtraction:
    """Normalize GLiNER spans while independently deciding sentence eligibility."""

    source = job_description or ""
    if not source.strip():
        return RequirementExtraction(
            status="failed",
            source_hash=hashlib.sha256(source.encode("utf-8")).hexdigest(),
            extractor_version=extractor_version,
            warnings=["empty_job_description"],
        )
    spans = _coerce_spans(source, model_output)
    requirements: list[Requirement] = []
    warnings: list[str] = []
    for sentence in _all_sentences(source):
        eligible, confidence, signals = _candidate_eligibility(sentence, spans)
        if not eligible:
            if any(span.label in _CONCEPT_LABELS and _overlaps(span, sentence) for span in spans):
                warnings.append(f"concept_spans_not_promoted:{sentence.start}")
            continue
        requirements.append(_build_requirement(sentence, spans, len(requirements) + 1, extractor_version, confidence, signals))
    return RequirementExtraction(
        status="evaluated",
        source_hash=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        extractor_version=extractor_version,
        requirements=requirements,
        warnings=warnings[:100],
    )


class ScannerRequirementExtractor:
    """New scanner extraction contract over the shared lazy GLiNER runtime."""

    def __init__(self, *, model: EntityModel | None = None, extractor_version: str = SCANNER_EXTRACTOR_VERSION) -> None:
        self.model = model
        self.extractor_version = extractor_version
        self._inference_lock = threading.Lock()

    def extract(self, job_description: str) -> RequirementExtraction:
        source = job_description or ""
        if not source.strip():
            return extract_requirements_from_entities(source, {}, extractor_version=self.extractor_version)
        if self.model is not None:
            try:
                with self._inference_lock:
                    output = self.model.extract_entities(
                        source,
                        MODEL_LABELS,
                        include_confidence=True,
                        include_spans=True,
                        overlap_policy="flat",
                    )
            except Exception as exc:
                logger.exception("scanner_requirement_extraction_failed")
                raise RequirementExtractionError() from exc
            return extract_requirements_from_entities(source, output, extractor_version=self.extractor_version)

        provider = get_requirement_extractor()
        extract_raw = getattr(provider, "extract_raw_spans", None)
        if not callable(extract_raw):
            raise RequirementExtractionError("The configured GLiNER provider cannot return raw entity spans")
        spans = extract_raw(source)
        provider_version = f"{getattr(provider, 'model_name', 'gliner2')}@{getattr(provider, 'revision', 'default')}"
        return extract_requirements_from_entities(source, spans, extractor_version=provider_version)


__all__ = [
    "SCANNER_EXTRACTOR_VERSION",
    "CandidateTextSegment",
    "ScannerRequirementExtractor",
    "candidate_facing_segments",
    "extract_requirements_from_entities",
]
