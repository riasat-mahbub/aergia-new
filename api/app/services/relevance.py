"""Deterministic requirement/keyword extraction, Library matching, and CV relevance.

The ``requirement-v2`` contract is intentionally self-contained. It performs no
network, renderer, subprocess, or model inference. FTS5 is used only as an
in-memory lexical ranker, so a saved job can be reproduced from its input text
and the user's Library/CV snapshot. The older ``keyword-v1`` helpers remain
available for reading legacy results.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from datetime import date, datetime
from math import log2

from app.schemas.application import (
    ExtractedKeyword,
    JobRequirement,
    MatchEvidence,
    RequirementEvidence,
    RequirementMatch,
    RequirementRelevanceResult,
    RelevanceResult,
)
from app.services.relevance_taxonomy import ALIAS_TO_CANONICAL, TAXONOMY

ALGORITHM_VERSION = "keyword-v1"
REQUIREMENT_ALGORITHM_VERSION = "requirement-v2"
MAX_KEYWORDS = 30
MAX_REQUIREMENTS = 40
ENTRY_RELEVANCE_THRESHOLD = 0.35
MAX_FIT_PASSES = 64
REQUIREMENT_COVERAGE_THRESHOLD = 0.65
MIN_SELECTION_GAIN = 0.03
COMPLEMENTARY_EVIDENCE_BONUS = 0.18
MAX_COMPLEMENTARY_SECTIONS = {
    "hard_skill": 3,
    "responsibility": 2,
    "quantitative": 2,
    "education": 2,
    "certification": 2,
    "language": 2,
    "project": 2,
    "research": 2,
    "other": 2,
}

try:  # RapidFuzz is the production implementation; the fallback keeps tests portable.
    from rapidfuzz.fuzz import ratio as _rapidfuzz_ratio
except ImportError:  # pragma: no cover - exercised only in minimal environments
    _rapidfuzz_ratio = None

KEYWORD_EXTRACTION_ERROR = "Job description does not contain enough text to extract keywords"

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "for",
        "from",
        "has",
        "have",
        "how",
        "in",
        "including",
        "is",
        "it",
        "job",
        "may",
        "must",
        "of",
        "on",
        "or",
        "our",
        "role",
        "should",
        "that",
        "the",
        "their",
        "this",
        "to",
        "we",
        "what",
        "when",
        "where",
        "who",
        "why",
        "will",
        "with",
        "work",
        "you",
        "your",
        "candidate",
        "candidates",
        "responsibility",
        "responsibilities",
        "requirement",
        "requirements",
        "qualification",
        "qualifications",
        "preferred",
    }
)

# Technical punctuation is accepted only inside a token.  The two branches
# cover leading-dot names (``.NET``) and word-start names (``C++``, ``CI/CD``).
_TOKEN_RE = re.compile(
    r"(?<![\w.])(?:\.[\w]+(?:[./-][\w+#./-]+)*|[\w]+(?:[+#]+[\w]*(?:[./-][\w+#./-]+)*|[./-][\w+#./-]+)*)",
    re.UNICODE,
)

_DASH_TRANSLATION = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2212": "-",
        "\ufe58": "-",
        "\ufe63": "-",
        "\uff0d": "-",
    }
)


@dataclass(frozen=True)
class _Token:
    text: str
    normalized: str
    start: int
    end: int


@dataclass
class _Candidate:
    text: str
    normalized: str
    tokens: tuple[str, ...]
    total_occurrences: int = 0
    role_occurrences: int = 0
    required_occurrences: int = 0
    preferred_occurrences: int = 0
    first_offset: int = 0
    library_presence: int = 0

    @property
    def weight(self) -> float:
        return (
            1.0
            + log2(self.total_occurrences)
            + 2.0 * self.role_occurrences
            + 1.0 * self.required_occurrences
            + 0.5 * self.preferred_occurrences
            + 0.5 * self.library_presence
        )


@dataclass(frozen=True)
class LibraryField:
    section_type: str
    library_entry_id: str | None
    source_row_id: str | None
    field_path: str
    text: str


@dataclass(frozen=True)
class ScoredLibraryRow:
    kind: str
    section_type: str
    library_entry_id: str | None
    source_row_id: str | None
    payload: dict
    score: float
    normalized_score: float
    order: int
    covered_requirement_ids: tuple[str, ...] = ()
    selection_gain: float = 0.0
    selection_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScoredSkillItem:
    """Keyword contribution for one item inside a skill group."""

    library_entry_id: str | None
    source_row_id: str | None
    item_index: int
    text: str
    score: float
    order: int


@dataclass(frozen=True)
class _LibraryRow:
    kind: str
    section_type: str
    library_entry_id: str | None
    source_row_id: str | None
    payload: dict
    fields: tuple[LibraryField, ...]
    order: int


LIBRARY_KIND_TO_SECTION_TYPE: dict[str, str] = {
    "experience": "experience",
    "education": "education",
    "skill": "skills",
    "project": "projects",
    "certification": "certifications",
    "language": "languages",
    "research": "research",
}

# These are evidence affinities, not a section hierarchy. They describe which
# sections can naturally prove a requirement. A strong match in a lower-affinity
# section can still win when it is the only or best available evidence.
_REQUIREMENT_SECTION_AFFINITY: dict[str, dict[str, float]] = {
    "hard_skill": {
        "skills": 0.95,
        "experience": 0.9,
        "projects": 0.85,
        "research": 0.45,
    },
    "responsibility": {
        "experience": 1.0,
        "projects": 0.8,
        "research": 0.55,
    },
    "quantitative": {
        "experience": 1.0,
        "projects": 0.85,
        "skills": 0.65,
    },
    "education": {"education": 1.0, "experience": 0.45},
    "certification": {"certifications": 1.0, "experience": 0.75},
    "language": {"languages": 1.0, "experience": 0.65},
    "project": {"projects": 1.0, "experience": 0.85, "skills": 0.7},
    "research": {"research": 1.0, "experience": 0.85, "projects": 0.6, "education": 0.5},
    "other": {"experience": 0.8, "projects": 0.7, "skills": 0.65},
}

# These are deliberately closed.  Contact fields, dates, IDs, URLs, styles,
# booleans, and metadata never enter keyword matching.
_LIBRARY_FIELDS: dict[str, tuple[str, ...]] = {
    "education": ("institution", "degree", "gpa", "summary"),
    "skill": ("category", "items"),
    "experience": ("company", "position", "location", "description"),
    "language": ("language", "proficiency", "level"),
    "certification": ("name", "issuer"),
    "project": ("name", "description", "tech_stack"),
    "research": ("title", "publication_value", "description"),
}


class KeywordExtractionError(ValueError):
    """Raised when a role/JD pair yields no eligible keyword candidates."""


def normalize_text(value: str | None) -> str:
    """Normalize text for exact matching while preserving technical punctuation."""
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value).translate(_DASH_TRANSLATION)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.casefold()


def _normalized_source(value: str) -> str:
    if not value:
        return ""
    return unicodedata.normalize("NFKC", value).translate(_DASH_TRANSLATION)


def _scan_tokens(value: str, offset: int = 0) -> list[_Token]:
    source = _normalized_source(value)
    return [
        _Token(
            text=match.group(0),
            normalized=normalize_text(match.group(0)),
            start=offset + match.start(),
            end=offset + match.end(),
        )
        for match in _TOKEN_RE.finditer(source)
    ]


def tokenize(value: str | None) -> list[str]:
    """Return normalized technical tokens in source order."""
    return [token.normalized for token in _scan_tokens(value or "")]


def _keep_candidate_token(token: _Token) -> bool:
    if token.normalized in _STOPWORDS:
        return False
    if len(token.normalized) == 1:
        return token.text.isupper() or token.text in {"C", "R"}
    return True


def _heading_kind(heading: str | None) -> tuple[bool, bool]:
    normalized = normalize_text(heading)
    required = any(marker in normalized for marker in ("require", "qualification", "must have", "what you need"))
    preferred = any(marker in normalized for marker in ("preferred", "nice to have", "bonus"))
    return required, preferred


def _is_blank_delimited_heading(lines: Sequence[str], index: int) -> bool:
    stripped = lines[index].strip()
    if not stripped or len(stripped) > 120:
        return False
    before_blank = index == 0 or not lines[index - 1].strip()
    after_blank = index == len(lines) - 1 or not lines[index + 1].strip()
    if not (before_blank and after_blank):
        return False
    return not re.search(r"[.!?,;]$", stripped)


def _is_heading(lines: Sequence[str], index: int) -> bool:
    stripped = lines[index].strip()
    return bool(stripped) and (stripped.endswith(":") or _is_blank_delimited_heading(lines, index))


def _job_line_contexts(lines: Sequence[str]) -> list[str | None]:
    current: str | None = None
    contexts: list[str | None] = []
    for index, line in enumerate(lines):
        if line.strip() and _is_heading(lines, index):
            current = line.strip().rstrip(":").strip()
        contexts.append(current)
    return contexts


def _source_lines(role: str, job_description: str) -> Iterable[tuple[str, str, int, bool, bool]]:
    role_text = role or ""
    jd_text = job_description or ""
    role_lines = role_text.splitlines() or ([role_text] if role_text else [])
    jd_lines = jd_text.splitlines() or ([jd_text] if jd_text else [])
    jd_contexts = _job_line_contexts(jd_lines)

    cursor = 0
    for line in role_lines:
        yield "role", line, cursor, False, False
        cursor += len(line) + 1

    cursor = len(role_text) + 1
    for index, line in enumerate(jd_lines):
        required, preferred = _heading_kind(jd_contexts[index])
        yield "job_description", line, cursor, required, preferred
        cursor += len(line) + 1


def _filtered_tokens(line: str, offset: int) -> list[_Token]:
    return [token for token in _scan_tokens(line, offset) if _keep_candidate_token(token)]


def _library_value(entry: object, key: str, default: object = None) -> object:
    if isinstance(entry, Mapping):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _as_kind(entry: object) -> str:
    raw_kind = _library_value(entry, "kind", "")
    return str(getattr(raw_kind, "value", raw_kind))


def _as_id(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _rich_text_parts(value: object) -> list[str]:
    """Extract canonical rich-text runs/list items, excluding arbitrary metadata."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            parts.extend(_rich_text_parts(item))
        return parts
    if isinstance(value, Mapping):
        parts = []
        for key in ("text", "value"):
            text = value.get(key)
            if isinstance(text, str):
                parts.append(text)
        for key in ("root", "children", "items", "content"):
            if key in value:
                parts.extend(_rich_text_parts(value[key]))
        return parts
    return []


def _field_text(value: object) -> str:
    return " ".join(part.strip() for part in _rich_text_parts(value) if part.strip())


def _row_fields(
    *,
    kind: str,
    row: Mapping[str, object],
    entry_id: str | None,
    row_id: str | None,
    row_path: str,
) -> tuple[LibraryField, ...]:
    section_type = LIBRARY_KIND_TO_SECTION_TYPE[kind]
    fields: list[LibraryField] = []
    for field_name in _LIBRARY_FIELDS[kind]:
        text = _field_text(row.get(field_name))
        if text:
            fields.append(
                LibraryField(
                    section_type=section_type,
                    library_entry_id=entry_id,
                    source_row_id=row_id,
                    field_path=f"{row_path}.{field_name}",
                    text=text,
                )
            )
    return tuple(fields)


def _library_rows(entries: Iterable[object]) -> list[_LibraryRow]:
    rows: list[_LibraryRow] = []
    order = 0
    for entry in entries:
        kind = _as_kind(entry)
        if kind not in _LIBRARY_FIELDS:
            continue
        entry_id = _as_id(_library_value(entry, "id"))
        payload = _library_value(entry, "payload", [])
        if not isinstance(payload, list):
            continue
        for row_index, raw_row in enumerate(payload):
            if not isinstance(raw_row, Mapping):
                continue
            row = dict(raw_row)
            row_id = _as_id(row.get("id"))
            rows.append(
                _LibraryRow(
                    kind=kind,
                    section_type=LIBRARY_KIND_TO_SECTION_TYPE[kind],
                    library_entry_id=entry_id,
                    source_row_id=row_id,
                    payload=row,
                    fields=_row_fields(
                        kind=kind,
                        row=row,
                        entry_id=entry_id,
                        row_id=row_id,
                        row_path=f"payload[{row_index}]",
                    ),
                    order=order,
                )
            )
            order += 1
    return rows


def flatten_library_entry(entry: object) -> list[LibraryField]:
    """Flatten one eligible Library entry to its user-visible matching fields."""
    return [field for row in _library_rows([entry]) for field in row.fields]


def flatten_library_fields(entries: Iterable[object]) -> list[LibraryField]:
    """Flatten eligible Library rows without exposing IDs/metadata as text."""
    return [field for row in _library_rows(entries) for field in row.fields]


def flatten_profile_fields(profile: Mapping[str, object] | object) -> list[LibraryField]:
    """Return only the profile title and summary for CV relevance matching."""
    fields: list[LibraryField] = []
    for key in ("title", "summary"):
        text = _field_text(_library_value(profile, key))
        if text:
            fields.append(
                LibraryField(
                    section_type="profile",
                    library_entry_id=None,
                    source_row_id=None,
                    field_path=f"profile.{key}",
                    text=text,
                )
            )
    return fields


def flatten_cv_fields(sections: Sequence[object] | Mapping[str, object]) -> list[LibraryField]:
    """Flatten a persisted CV using the same eligible field policy as Library."""
    if isinstance(sections, Mapping):
        sections = sections.get("sections", [])  # type: ignore[assignment]
    if not isinstance(sections, Sequence) or isinstance(sections, (str, bytes)):
        return []

    fields: list[LibraryField] = []
    for section_index, raw_section in enumerate(sections):
        if not isinstance(raw_section, Mapping):
            continue
        if raw_section.get("enabled") is False:
            continue
        section_type = str(raw_section.get("type", ""))
        if section_type == "profile":
            data = raw_section.get("data")
            if isinstance(data, Mapping):
                for key in ("title", "summary"):
                    text = _field_text(data.get(key))
                    if text:
                        fields.append(
                            LibraryField(
                                section_type="profile",
                                library_entry_id=None,
                                source_row_id=None,
                                field_path=f"sections[{section_index}].data.{key}",
                                text=text,
                            )
                        )
            continue

        kind = next((candidate for candidate, section in LIBRARY_KIND_TO_SECTION_TYPE.items() if section == section_type), None)
        if kind is None:
            continue
        data = raw_section.get("data")
        if not isinstance(data, list):
            continue
        for row_index, raw_row in enumerate(data):
            if not isinstance(raw_row, Mapping):
                continue
            fields.extend(
                _row_fields(
                    kind=kind,
                    row=raw_row,
                    entry_id=None,
                    row_id=_as_id(raw_row.get("id")),
                    row_path=f"sections[{section_index}].data[{row_index}]",
                )
            )
    return fields


def _contains_sequence(haystack: Sequence[str], needle: Sequence[str]) -> bool:
    if not needle or len(needle) > len(haystack):
        return False
    width = len(needle)
    return any(tuple(haystack[index : index + width]) == tuple(needle) for index in range(len(haystack) - width + 1))


def _field_tokens(field: LibraryField) -> list[str]:
    return [token.normalized for token in _scan_tokens(field.text)]


def extract_keywords(
    role: str,
    job_description: str,
    library_entries: Iterable[object] = (),
) -> list[ExtractedKeyword]:
    """Extract and weight up to ``MAX_KEYWORDS`` deterministic job terms."""
    candidates: dict[str, _Candidate] = {}
    for source, line, offset, required, preferred in _source_lines(role or "", job_description or ""):
        tokens = _filtered_tokens(line, offset)
        for width in (1, 2, 3):
            for start in range(len(tokens) - width + 1):
                gram = tokens[start : start + width]
                normalized_tokens = tuple(token.normalized for token in gram)
                normalized = " ".join(normalized_tokens)
                candidate = candidates.get(normalized)
                if candidate is None:
                    candidate = _Candidate(
                        text=" ".join(token.text for token in gram),
                        normalized=normalized,
                        tokens=normalized_tokens,
                        first_offset=gram[0].start,
                    )
                    candidates[normalized] = candidate
                candidate.total_occurrences += 1
                if source == "role":
                    candidate.role_occurrences += 1
                if required:
                    candidate.required_occurrences += 1
                if preferred:
                    candidate.preferred_occurrences += 1

    if not candidates:
        raise KeywordExtractionError(KEYWORD_EXTRACTION_ERROR)

    library_fields = flatten_library_fields(library_entries)
    library_tokens = [_field_tokens(field) for field in library_fields]
    for candidate in candidates.values():
        if any(_contains_sequence(tokens, candidate.tokens) for tokens in library_tokens):
            candidate.library_presence = 1

    ordered = sorted(
        candidates.values(),
        key=lambda candidate: (-candidate.weight, -len(candidate.tokens), candidate.first_offset),
    )
    selected: list[_Candidate] = []
    for candidate in ordered:
        if any(_contains_sequence(previous.tokens, candidate.tokens) for previous in selected):
            continue
        selected.append(candidate)
        if len(selected) >= MAX_KEYWORDS:
            break

    return [
        ExtractedKeyword(
            text=candidate.text,
            normalized=candidate.normalized,
            weight=candidate.weight,
        )
        for candidate in selected
    ]


def _coerce_keywords(keywords: Iterable[ExtractedKeyword | Mapping[str, object] | str]) -> list[ExtractedKeyword]:
    result: list[ExtractedKeyword] = []
    for keyword in keywords:
        if isinstance(keyword, ExtractedKeyword):
            result.append(keyword)
        elif isinstance(keyword, str):
            normalized = normalize_text(keyword)
            if normalized:
                result.append(ExtractedKeyword(text=keyword, normalized=normalized, weight=1.0))
        else:
            result.append(ExtractedKeyword.model_validate(keyword))
    return result


def score_library_rows(
    keywords: Iterable[ExtractedKeyword | Mapping[str, object] | str],
    library_entries: Iterable[object],
) -> list[ScoredLibraryRow]:
    """Score each eligible Library payload row by distinct keyword coverage."""
    extracted = _coerce_keywords(keywords)
    rows = _library_rows(library_entries)
    raw_scores: list[tuple[_LibraryRow, float]] = []
    for row in rows:
        score = 0.0
        for keyword in extracted:
            keyword_tokens = tuple(normalize_text(keyword.normalized).split())
            if any(_contains_sequence(_field_tokens(field), keyword_tokens) for field in row.fields):
                score += keyword.weight
        raw_scores.append((row, score))

    maximum_by_kind: dict[str, float] = {}
    for row, score in raw_scores:
        if score > maximum_by_kind.get(row.kind, 0.0):
            maximum_by_kind[row.kind] = score

    return [
        ScoredLibraryRow(
            kind=row.kind,
            section_type=row.section_type,
            library_entry_id=row.library_entry_id,
            source_row_id=row.source_row_id,
            payload=row.payload,
            score=score,
            normalized_score=(score / maximum_by_kind[row.kind] if score > 0 else 0.0),
            order=row.order,
        )
        for row, score in raw_scores
    ]


def select_relevant_library_rows(
    keywords: Iterable[ExtractedKeyword | Mapping[str, object] | str],
    library_entries: Iterable[object],
    threshold: float = ENTRY_RELEVANCE_THRESHOLD,
) -> list[ScoredLibraryRow]:
    """Select rows at or above the per-kind normalized relevance threshold."""
    scored = score_library_rows(keywords, library_entries)
    return [row for row in scored if row.score > 0 and row.normalized_score >= threshold]


def score_skill_items(
    keywords: Iterable[ExtractedKeyword | Mapping[str, object] | str],
    row: ScoredLibraryRow,
) -> list[ScoredSkillItem]:
    """Score individual skill items for deterministic fit trimming.

    A skill group is selected at row level, but its individual items can have
    very different relevance. Keeping this calculation separate lets the fit
    loop remove low-value chips before dropping an entire library row.
    """

    if row.kind != "skill" or not isinstance(row.payload.get("items"), list):
        return []
    extracted = _coerce_keywords(keywords)
    scored: list[ScoredSkillItem] = []
    for item_index, raw_item in enumerate(row.payload["items"]):
        text = _field_text(raw_item)
        if not text:
            continue
        item_tokens = _field_tokens(
            LibraryField(
                section_type="skills",
                library_entry_id=row.library_entry_id,
                source_row_id=row.source_row_id,
                field_path=f"items[{item_index}]",
                text=text,
            )
        )
        score = 0.0
        for keyword in extracted:
            keyword_tokens = tuple(normalize_text(keyword.normalized).split())
            if keyword_tokens and _contains_sequence(item_tokens, keyword_tokens):
                score += keyword.weight
        scored.append(
            ScoredSkillItem(
                library_entry_id=row.library_entry_id,
                source_row_id=row.source_row_id,
                item_index=item_index,
                text=text,
                score=score,
                order=row.order,
            )
        )
    return scored


def _cv_fields_with_profile(
    sections: Sequence[object] | Mapping[str, object], profile: Mapping[str, object] | object | None,
) -> list[LibraryField]:
    fields = flatten_cv_fields(sections)
    if profile is not None:
        fields = [*flatten_profile_fields(profile), *fields]
    return fields


def _snippet(text: str) -> str:
    compact = normalize_text(text)
    if len(compact) <= 240:
        return text.strip()
    return f"{text.strip()[:237]}..."


def calculate_relevance(
    keywords: Iterable[ExtractedKeyword | Mapping[str, object] | str],
    sections: Sequence[object] | Mapping[str, object] | None = None,
    *,
    fields: Iterable[LibraryField] | None = None,
    profile: Mapping[str, object] | object | None = None,
) -> RelevanceResult:
    """Calculate weighted distinct-keyword coverage for a CV payload."""
    extracted = _coerce_keywords(keywords)
    matching_fields = list(fields) if fields is not None else _cv_fields_with_profile(sections or [], profile)
    matched_keywords: list[str] = []
    missing_keywords: list[str] = []
    evidence: list[MatchEvidence] = []
    matched_weight = 0.0

    for keyword in extracted:
        keyword_tokens = tuple(normalize_text(keyword.normalized).split())
        matches = [field for field in matching_fields if _contains_sequence(_field_tokens(field), keyword_tokens)]
        if not matches:
            missing_keywords.append(keyword.text)
            continue
        matched_keywords.append(keyword.text)
        matched_weight += keyword.weight
        for field in matches:
            evidence.append(
                MatchEvidence(
                    keyword=keyword.text,
                    section_type=field.section_type,
                    library_entry_id=field.library_entry_id,
                    source_row_id=field.source_row_id,
                    field_path=field.field_path,
                    snippet=_snippet(field.text),
                )
            )

    total_weight = sum(keyword.weight for keyword in extracted)
    score = round(100 * matched_weight / total_weight) if total_weight else 0
    return RelevanceResult(
        score=score,
        matched_weight=matched_weight,
        total_weight=total_weight,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        evidence=evidence,
        algorithm_version=ALGORITHM_VERSION,
    )


# ---------------------------------------------------------------------------
# requirement-v2
# ---------------------------------------------------------------------------


@dataclass
class _RequirementDraft:
    text: str
    normalized: str
    canonical: str | None
    requirement_type: str
    required: bool
    weight: float
    constraint: dict[str, object] | None


@dataclass(frozen=True)
class _RequirementMatchData:
    requirement: JobRequirement
    covered: bool
    score: float
    matched_by: tuple[str, ...]
    evidence: RequirementEvidence | None


@dataclass(frozen=True)
class _FieldMatch:
    field: LibraryField
    score: float
    method: str


_YEARS_RE = re.compile(r"\b(\d+)\+?\s*(?:years?|yrs?)\b", re.IGNORECASE)
_DEGREE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("phd", re.compile(r"\b(?:ph\.?d\.?|doctorate|doctoral)\b", re.IGNORECASE)),
    ("master", re.compile(r"(?<!\w)(?:master(?:'s)?|msc|m\.?s\.?|mba)(?!\w)", re.IGNORECASE)),
    ("bachelor", re.compile(r"(?<!\w)(?:bachelor(?:'s)?|bsc|b\.?s\.?|undergraduate)(?!\w)", re.IGNORECASE)),
    ("associate", re.compile(r"(?<!\w)(?:associate(?:'s)?|a\.?a\.?|a\.?s\.?)(?!\w)", re.IGNORECASE)),
)
_DEGREE_RANK = {"associate": 1, "bachelor": 2, "master": 3, "phd": 4}
_CERTIFICATION_CUE_RE = re.compile(
    r"\b(?:certificat(?:e|ion)|certified|licen[cs]e[sd]?|ccna|ccnp|cissp|pmp|comptia|itil)\b",
    re.IGNORECASE,
)
_LANGUAGE_CUE_RE = re.compile(
    r"\b(?:fluent|fluency|bilingual|multilingual|spoken|written|language proficiency|language skills)\b",
    re.IGNORECASE,
)
_COMMON_LANGUAGE_NAMES = frozenset(
    {
        "arabic",
        "chinese",
        "dutch",
        "english",
        "french",
        "german",
        "hindi",
        "italian",
        "japanese",
        "korean",
        "mandarin",
        "portuguese",
        "russian",
        "spanish",
    }
)
_PROJECT_CUE_RE = re.compile(
    r"\b(?:project|portfolio|side project|personal project|capstone|shipped product)\b",
    re.IGNORECASE,
)
_RESEARCH_CUE_RE = re.compile(
    r"\b(?:research|publication|published|laboratory|lab|thesis|academic|peer[- ]reviewed)\b",
    re.IGNORECASE,
)


def _clean_requirement_line(line: str) -> str:
    cleaned = re.sub(r"^\s*(?:[-*•▪‣]|\d+[.)])\s*", "", line).strip()
    return re.sub(r"\s+", " ", cleaned)


def _requirement_type_for_line(
    line: str,
    context: str | None,
    taxonomy_hits: Sequence[tuple[str, str, str]],
    *,
    has_degree: bool,
    has_years: bool,
) -> str:
    """Infer the evidence family a job line naturally needs.

    This is deliberately a small, explainable cue map. It does not decide
    which section must be selected: the selector still scores every row that
    can support the requirement.
    """

    text = normalize_text(f"{context or ''} {line}")
    if has_degree:
        return "education"
    if _CERTIFICATION_CUE_RE.search(text):
        return "certification"
    if _LANGUAGE_CUE_RE.search(text) or normalize_text(line) in _COMMON_LANGUAGE_NAMES:
        return "language"
    if _RESEARCH_CUE_RE.search(text):
        return "research"
    if _PROJECT_CUE_RE.search(text):
        return "project"
    if taxonomy_hits:
        return taxonomy_hits[0][1]
    if has_years:
        return "quantitative"
    return "other"


def _free_text_subject(line: str, requirement_type: str) -> str:
    """Remove section wording so bounded prose matches its useful subject."""

    markers = {
        "certification": r"\b(?:certificat(?:e|ion)|certified|licen[cs]e[sd]?)\b",
        "language": r"\b(?:language proficiency|language skills|fluent|fluency|bilingual|multilingual|spoken|written)\b",
        "project": r"\b(?:project|portfolio|side project|personal project|capstone|shipped product)\b",
        "research": r"\b(?:publication|publications|published|laboratory|lab|thesis|academic|peer[- ]reviewed)\b",
    }
    subject = re.sub(markers.get(requirement_type, r"$^"), " ", line, flags=re.IGNORECASE)
    subject = re.sub(
        r"\b(?:required|preferred|desirable|optional|nice to have|bonus|plus)\b",
        " ",
        subject,
        flags=re.IGNORECASE,
    )
    subject = re.sub(r"\s+", " ", subject).strip(" .,;:-")
    return subject or line


def _requirement_priority(source: str, line: str, context: str | None) -> tuple[bool, bool]:
    """Return required/preferred flags without treating a negated heading as required."""
    text = normalize_text(f"{context or ''} {line}")
    optional = re.search(r"\b(?:not required|not necessary|optional|nice to have|bonus|plus)\b", text)
    preferred = bool(optional or re.search(r"\b(?:preferred|desirable|advantage)\b", text))
    required = not preferred
    if source == "role":
        # A role can help identify a skill, but should not make a title match
        # outweigh actual qualification requirements.
        required = False
    if re.search(r"\b(?:required|must have|must be able|you will need|what you need)\b", text):
        required = True
        preferred = False
    if optional:
        required = False
        preferred = True
    return required, preferred


def _taxonomy_hits(text: str) -> list[tuple[str, str, str]]:
    """Find canonical concepts once, preferring longer aliases within a concept."""
    tokens = tokenize(text)
    hits: list[tuple[int, str, str, str]] = []
    for canonical, (requirement_type, aliases) in TAXONOMY.items():
        best: tuple[int, int, str] | None = None
        for alias in sorted(aliases, key=lambda value: len(tokenize(value)), reverse=True):
            alias_tokens = tokenize(alias)
            if not alias_tokens:
                continue
            for index in range(len(tokens) - len(alias_tokens) + 1):
                if tuple(tokens[index : index + len(alias_tokens)]) == tuple(alias_tokens):
                    candidate = (index, -len(alias_tokens), alias)
                    if best is None or candidate[:2] < best[:2]:
                        best = candidate
                    break
        if best is not None:
            hits.append((best[0], canonical, requirement_type, best[2]))
    hits.sort(key=lambda item: (item[0], -len(tokenize(item[3])), item[1]))
    seen: set[str] = set()
    unique_hits: list[tuple[str, str, str]] = []
    for _index, canonical, requirement_type, alias in hits:
        if canonical in seen:
            continue
        seen.add(canonical)
        unique_hits.append((canonical, requirement_type, alias))
    return unique_hits


def _taxonomy_aliases(canonical: str | None) -> tuple[str, ...]:
    if not canonical:
        return ()
    return TAXONOMY.get(canonical, ("", ()))[1]


def _is_requirement_heading(lines: Sequence[str], index: int) -> bool:
    """Recognize section labels without mistaking a one-line JD for a heading."""
    stripped = lines[index].strip().rstrip(":")
    if not stripped:
        return False
    normalized = normalize_text(stripped)
    if lines[index].strip().endswith(":"):
        return True
    known_headings = (
        "requirements",
        "qualifications",
        "minimum qualifications",
        "preferred qualifications",
        "required skills",
        "preferred skills",
        "nice to have",
        "bonus",
        "responsibilities",
        "what you bring",
        "what you need",
        "about the role",
    )
    return normalized in known_headings


def _requirement_lines(role: str, job_description: str) -> Iterable[tuple[str, str, str | None, bool]]:
    role_text = role or ""
    if role_text.strip():
        for line in role_text.splitlines() or [role_text]:
            yield "role", line, None, False

    jd_text = job_description or ""
    lines = jd_text.splitlines() or ([jd_text] if jd_text else [])
    current_context: str | None = None
    for index, line in enumerate(lines):
        is_heading = _is_requirement_heading(lines, index)
        if is_heading and line.strip():
            current_context = line.strip().rstrip(":").strip()
        yield "job_description", line, current_context, is_heading


def _draft_weight(required: bool, preferred: bool) -> float:
    if required:
        return 2.0
    if preferred:
        return 1.0
    return 0.75


def extract_requirements(role: str, job_description: str) -> list[JobRequirement]:
    """Parse a job into atomic taxonomy, constraint, and bounded free-text requirements."""
    drafts: dict[tuple[object, ...], _RequirementDraft] = {}
    allow_role_fallback = not bool((job_description or "").strip())
    for source, raw_line, context, is_heading in _requirement_lines(role, job_description):
        line = _clean_requirement_line(raw_line)
        if not line or is_heading:
            continue
        tokens = _filtered_tokens(line, 0)
        if not tokens:
            continue
        required, preferred = _requirement_priority(source, line, context)
        weight = _draft_weight(required, preferred)
        hits = _taxonomy_hits(line)
        years_match = _YEARS_RE.search(line)
        degree_level = next((level for level, pattern in _DEGREE_PATTERNS if pattern.search(line)), None)
        line_type = _requirement_type_for_line(
            line,
            context,
            hits,
            has_degree=bool(degree_level or re.search(r"\bdegree\b", line, re.IGNORECASE)),
            has_years=bool(years_match),
        )

        for canonical, requirement_type, _alias in hits:
            key = ("concept", canonical)
            existing = drafts.get(key)
            if existing is None or (required and not existing.required):
                drafts[key] = _RequirementDraft(
                    text=canonical,
                    normalized=normalize_text(canonical),
                    canonical=canonical,
                    requirement_type=line_type if line_type != "other" else requirement_type,
                    required=required or (existing.required if existing else False),
                    weight=max(weight, existing.weight if existing else 0.0),
                    constraint=None,
                )
            elif existing is not None:
                existing.required = existing.required or required
                existing.weight = max(existing.weight, weight)

        if years_match:
            minimum = int(years_match.group(1))
            key = ("years", minimum)
            existing = drafts.get(key)
            constraint = {"kind": "years_experience", "minimum": minimum}
            if existing is None:
                drafts[key] = _RequirementDraft(
                    text=line,
                    normalized=normalize_text(line),
                    canonical=None,
                    requirement_type="quantitative",
                    required=required,
                    weight=weight,
                    constraint=constraint,
                )
            else:
                existing.required = existing.required or required
                existing.weight = max(existing.weight, weight)

        if degree_level or re.search(r"\bdegree\b", line, re.IGNORECASE):
            key = ("degree", degree_level or normalize_text(line))
            existing = drafts.get(key)
            constraint = {"kind": "degree_level", "minimum": degree_level} if degree_level else None
            if existing is None:
                drafts[key] = _RequirementDraft(
                    text=line,
                    normalized=normalize_text(line),
                    canonical=None,
                    requirement_type="education",
                    required=required,
                    weight=weight,
                    constraint=constraint,
                )
            else:
                existing.required = existing.required or required
                existing.weight = max(existing.weight, weight)

        if (
            source == "job_description" or allow_role_fallback
        ) and not hits and not years_match and not degree_level and not re.search(r"\bdegree\b", line, re.IGNORECASE):
            # A complete line is the bounded free-text unit.  This is useful
            # for a product name or responsibility absent from the taxonomy,
            # without generating every arbitrary JD n-gram.
            subject = _free_text_subject(line, line_type)
            key = ("text", normalize_text(subject))
            drafts.setdefault(
                key,
                _RequirementDraft(
                    text=subject,
                    normalized=normalize_text(subject),
                    canonical=None,
                    requirement_type=line_type,
                    required=required,
                    weight=weight,
                    constraint=None,
                ),
            )

    if not drafts:
        raise KeywordExtractionError(KEYWORD_EXTRACTION_ERROR)

    ordered = list(drafts.values())[:MAX_REQUIREMENTS]
    return [
        JobRequirement(
            id=f"req-{index:03d}",
            text=draft.text,
            normalized=draft.normalized,
            canonical=draft.canonical,
            type=draft.requirement_type,  # type: ignore[arg-type]
            required=draft.required,
            weight=draft.weight,
            constraint=draft.constraint,
        )
        for index, draft in enumerate(ordered, start=1)
    ]


def _coerce_requirements(requirements: Iterable[JobRequirement | Mapping[str, object] | str]) -> list[JobRequirement]:
    result: list[JobRequirement] = []
    for index, requirement in enumerate(requirements, start=1):
        if isinstance(requirement, JobRequirement):
            result.append(requirement)
        elif isinstance(requirement, str):
            normalized = normalize_text(requirement)
            canonical = ALIAS_TO_CANONICAL.get(normalized)
            requirement_type = TAXONOMY.get(canonical, ("other", ()))[0] if canonical else "other"
            result.append(
                JobRequirement(
                    id=f"req-{index:03d}",
                    text=requirement,
                    normalized=normalized,
                    canonical=canonical,
                    type=requirement_type,  # type: ignore[arg-type]
                    required=True,
                    weight=2.0,
                )
            )
        else:
            result.append(JobRequirement.model_validate(requirement))
    return result


def _fts_terms(text: str) -> list[str]:
    # FTS5 receives safe alphanumeric terms. Taxonomy matching above retains
    # technical punctuation such as C++, .NET, and CI/CD.
    terms: list[str] = []
    for token in tokenize(text):
        terms.extend(re.findall(r"[a-z0-9]+", token))
    return [term for term in terms if term not in _STOPWORDS and len(term) > 1]


def _best_fts_match(requirement: JobRequirement, fields: Sequence[LibraryField]) -> _FieldMatch | None:
    terms = _fts_terms(requirement.text)
    if not terms or not fields:
        return None
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE relevance_fields USING fts5(field_index UNINDEXED, text)")
        connection.executemany(
            "INSERT INTO relevance_fields(field_index, text) VALUES (?, ?)",
            [(index, field.text) for index, field in enumerate(fields)],
        )
        query = " OR ".join(f'"{term.replace(chr(34), "")}"' for term in terms)
        rows = connection.execute(
            "SELECT field_index, bm25(relevance_fields) FROM relevance_fields "
            "WHERE relevance_fields MATCH ? ORDER BY bm25(relevance_fields), field_index LIMIT 25",
            (query,),
        ).fetchall()
    except sqlite3.OperationalError:
        return None
    finally:
        connection.close()

    best: _FieldMatch | None = None
    best_index = -1
    required_terms = set(terms)
    for index, _rank in rows:
        field_terms = set(_fts_terms(fields[index].text))
        overlap = len(required_terms & field_terms) / len(required_terms)
        if len(required_terms) > 1 and overlap < 0.75:
            continue
        score = min(0.95, 0.55 + 0.4 * overlap)
        candidate = _FieldMatch(field=fields[index], score=score, method="fts5")
        if best is None or (candidate.score, -index) > (best.score, -best_index):
            best = candidate
            best_index = index
    return best


def _fuzzy_ratio(left: str, right: str) -> float:
    if _rapidfuzz_ratio is not None:
        return float(_rapidfuzz_ratio(left, right)) / 100.0
    return SequenceMatcher(None, left, right).ratio()


def _best_fuzzy_match(requirement: JobRequirement, fields: Sequence[LibraryField]) -> _FieldMatch | None:
    aliases = _taxonomy_aliases(requirement.canonical) or (requirement.text,)
    best: _FieldMatch | None = None
    for field in fields[:200]:
        field_tokens = _field_tokens(field)
        for alias in aliases:
            alias_tokens = tokenize(alias)
            if not alias_tokens or len(" ".join(alias_tokens)) < 4:
                continue
            width = len(alias_tokens)
            for index in range(max(0, len(field_tokens) - width + 1)):
                value = " ".join(field_tokens[index : index + width])
                ratio = _fuzzy_ratio(" ".join(alias_tokens), value)
                if ratio < 0.9:
                    continue
                candidate = _FieldMatch(field=field, score=0.8 + 0.15 * (ratio - 0.9) / 0.1, method="fuzzy")
                if best is None or candidate.score > best.score:
                    best = candidate
    return best


def _degree_rank(text: str) -> int:
    return max((_DEGREE_RANK[level] for level, pattern in _DEGREE_PATTERNS if pattern.search(text)), default=0)


def _parse_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip()
    try:
        if re.fullmatch(r"\d{4}", candidate):
            return date(int(candidate), 1, 1)
        if re.fullmatch(r"\d{4}-\d{2}", candidate):
            return date.fromisoformat(f"{candidate}-01")
        return date.fromisoformat(candidate[:10])
    except ValueError:
        return None


def _years_from_rows(rows: Iterable[Mapping[str, object]]) -> float:
    intervals: list[tuple[date, date]] = []
    today = date.today()
    for row in rows:
        start = _parse_date(row.get("start_date"))
        if start is None:
            continue
        end = today if row.get("current") else (_parse_date(row.get("end_date")) or today)
        if end >= start:
            intervals.append((start, end))
    if not intervals:
        return 0.0
    intervals.sort()
    merged: list[list[date]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return sum((end - start).days for start, end in merged) / 365.25


def _years_from_fields(fields: Sequence[LibraryField]) -> float:
    values = [int(match.group(1)) for field in fields for match in _YEARS_RE.finditer(field.text)]
    return float(max(values, default=0))


def _years_from_sections(sections: Sequence[object] | Mapping[str, object] | None) -> float:
    if isinstance(sections, Mapping):
        sections = sections.get("sections", [])  # type: ignore[assignment]
    if not isinstance(sections, Sequence) or isinstance(sections, (str, bytes)):
        return 0.0
    rows: list[Mapping[str, object]] = []
    for section in sections:
        if (
            not isinstance(section, Mapping)
            or section.get("enabled") is False
            or section.get("type") != "experience"
        ):
            continue
        data = section.get("data")
        if isinstance(data, list):
            rows.extend(row for row in data if isinstance(row, Mapping))
    return _years_from_rows(rows)


def _constraint_match(
    requirement: JobRequirement,
    fields: Sequence[LibraryField],
    experience_years: float | None,
) -> _FieldMatch | None:
    constraint = requirement.constraint or {}
    kind = constraint.get("kind")
    if kind == "years_experience":
        years = experience_years if experience_years is not None else _years_from_fields(fields)
        minimum = float(constraint.get("minimum", 0))
        if years < minimum:
            return None
        field = next((field for field in fields if field.section_type == "experience"), fields[0] if fields else None)
        if field is None:
            field = LibraryField(
                section_type="experience",
                library_entry_id=None,
                source_row_id=None,
                field_path="experience.duration",
                text=f"{years:.1f} years of experience",
            )
        return _FieldMatch(field=field, score=1.0, method="constraint")
    if kind == "degree_level":
        minimum = _DEGREE_RANK.get(str(constraint.get("minimum", "")).casefold(), 0)
        for field in fields:
            if field.field_path.endswith(".degree") and _degree_rank(field.text) >= minimum:
                return _FieldMatch(field=field, score=1.0, method="constraint")
        return None
    return None


def _best_match(
    requirement: JobRequirement,
    fields: Sequence[LibraryField],
    *,
    experience_years: float | None = None,
) -> _FieldMatch | None:
    constrained = _constraint_match(requirement, fields, experience_years)
    if requirement.constraint:
        return constrained

    aliases = _taxonomy_aliases(requirement.canonical)
    if aliases:
        for field in fields:
            field_tokens = _field_tokens(field)
            for alias in aliases:
                alias_tokens = tokenize(alias)
                if _contains_sequence(field_tokens, alias_tokens):
                    return _FieldMatch(field=field, score=1.0, method="taxonomy")
    else:
        requirement_tokens = tokenize(requirement.normalized or requirement.text)
        for field in fields:
            if _contains_sequence(_field_tokens(field), requirement_tokens):
                return _FieldMatch(field=field, score=1.0, method="fts5")

    lexical = _best_fts_match(requirement, fields)
    if lexical is not None:
        return lexical
    return _best_fuzzy_match(requirement, fields)


def _to_evidence(match: _FieldMatch) -> RequirementEvidence:
    field = match.field
    return RequirementEvidence(
        section_type=field.section_type,
        library_entry_id=field.library_entry_id,
        source_row_id=field.source_row_id,
        field_path=field.field_path,
        snippet=_snippet(field.text),
        method=match.method,  # type: ignore[arg-type]
        score=round(match.score, 4),
    )


def _match_requirement(
    requirement: JobRequirement,
    fields: Sequence[LibraryField],
    *,
    experience_years: float | None = None,
) -> _RequirementMatchData:
    match = _best_match(requirement, fields, experience_years=experience_years)
    score = match.score if match else 0.0
    return _RequirementMatchData(
        requirement=requirement,
        covered=score >= REQUIREMENT_COVERAGE_THRESHOLD,
        score=round(score, 4),
        matched_by=(match.method,) if match else (),
        evidence=_to_evidence(match) if match else None,
    )


def _match_to_schema(match: _RequirementMatchData) -> RequirementMatch:
    return RequirementMatch(
        requirement=match.requirement,
        covered=match.covered,
        score=match.score,
        matched_by=list(match.matched_by),
        best_evidence=match.evidence,
    )


def not_evaluated_relevance(requirements: Iterable[JobRequirement | Mapping[str, object] | str]) -> RequirementRelevanceResult:
    extracted = _coerce_requirements(requirements)
    matches = [
        _match_to_schema(_RequirementMatchData(requirement=item, covered=False, score=0.0, matched_by=(), evidence=None))
        for item in extracted
    ]
    total_weight = sum(item.weight for item in extracted)
    return RequirementRelevanceResult(
        status="not_evaluated",
        score=None,
        coverage_score=None,
        required_score=None,
        preferred_score=None,
        matched_weight=0.0,
        total_weight=total_weight,
        covered_requirements=0,
        total_requirements=len(extracted),
        requirements=matches,
        algorithm_version=REQUIREMENT_ALGORITHM_VERSION,
    )


def evaluate_requirement_relevance(
    requirements: Iterable[JobRequirement | Mapping[str, object] | str],
    sections: Sequence[object] | Mapping[str, object] | None = None,
    *,
    fields: Iterable[LibraryField] | None = None,
    profile: Mapping[str, object] | object | None = None,
) -> RequirementRelevanceResult:
    """Evaluate each atomic requirement against its strongest CV evidence."""
    extracted = _coerce_requirements(requirements)
    matching_fields = list(fields) if fields is not None else _cv_fields_with_profile(sections or [], profile)
    experience_years = _years_from_sections(sections)
    if experience_years <= 0:
        experience_years = _years_from_fields(matching_fields)
    matches = [
        _match_requirement(item, matching_fields, experience_years=experience_years)
        for item in extracted
    ]

    total_weight = sum(item.requirement.weight for item in matches)
    matched_weight = sum(item.requirement.weight * item.score for item in matches)

    def component_score(predicate) -> int | None:
        component = [item for item in matches if predicate(item.requirement)]
        denominator = sum(item.requirement.weight for item in component)
        if not denominator:
            return None
        return round(100 * sum(item.requirement.weight * item.score for item in component) / denominator)

    return RequirementRelevanceResult(
        status="evaluated",
        score=round(100 * matched_weight / total_weight) if total_weight else 0,
        coverage_score=(
            round(100 * sum(item.requirement.weight for item in matches if item.covered) / total_weight)
            if total_weight
            else 0
        ),
        required_score=component_score(lambda item: item.required),
        preferred_score=component_score(lambda item: not item.required),
        matched_weight=round(matched_weight, 4),
        total_weight=round(total_weight, 4),
        covered_requirements=sum(1 for item in matches if item.covered),
        total_requirements=len(matches),
        requirements=[_match_to_schema(item) for item in matches],
        algorithm_version=REQUIREMENT_ALGORITHM_VERSION,
    )


def _section_affinity(requirement: JobRequirement, section_type: str) -> float:
    """Return how naturally a section proves one requirement family."""

    return _REQUIREMENT_SECTION_AFFINITY.get(requirement.type, {}).get(section_type, 0.0)


def _matches_for_library_row(
    requirements: Sequence[JobRequirement],
    row: _LibraryRow,
) -> list[_RequirementMatchData]:
    experience_years = _years_from_rows([row.payload]) if row.kind == "experience" else None
    return [
        _match_requirement(requirement, row.fields, experience_years=experience_years)
        for requirement in requirements
    ]


def _fields_for_scored_row(row: ScoredLibraryRow) -> tuple[LibraryField, ...]:
    return _row_fields(
        kind=row.kind,
        row=row.payload,
        entry_id=row.library_entry_id,
        row_id=row.source_row_id,
        row_path="payload[0]",
    )


def _selection_value(
    row: _LibraryRow,
    matches: Sequence[_RequirementMatchData],
    best_scores: Mapping[str, float],
    evidence_sections: Mapping[str, set[str]],
    total_weight: float,
) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    """Score a row by new evidence and complementary proof.

    The value is deliberately driven by the job requirements. Section
    affinities explain what evidence means, but never impose a global section
    ordering.
    """

    value = 0.0
    newly_covered: list[str] = []
    reasons: list[str] = []
    for match in matches:
        if match.score <= 0:
            continue
        requirement = match.requirement
        affinity = _section_affinity(requirement, row.section_type)
        if affinity <= 0:
            continue
        previous_score = best_scores.get(requirement.id, 0.0)
        improvement = max(0.0, match.score - previous_score)
        value += requirement.weight * improvement * affinity
        if improvement > 0:
            reasons.append(requirement.canonical or requirement.normalized)
            if match.covered and previous_score < REQUIREMENT_COVERAGE_THRESHOLD:
                newly_covered.append(requirement.id)

        # A direct skill plus a project/experience example is useful even when
        # both match the same requirement perfectly. Limit this to one extra
        # section so duplicate Library rows do not inflate selection.
        prior_sections = evidence_sections.get(requirement.id, set())
        if (
            match.score >= REQUIREMENT_COVERAGE_THRESHOLD
            and prior_sections
            and row.section_type not in prior_sections
            and len(prior_sections) < MAX_COMPLEMENTARY_SECTIONS.get(requirement.type, 2)
        ):
            value += requirement.weight * match.score * affinity * COMPLEMENTARY_EVIDENCE_BONUS
            reasons.append(f"complements:{requirement.canonical or requirement.normalized}")

    return (
        value / total_weight,
        tuple(dict.fromkeys(newly_covered)),
        tuple(dict.fromkeys(reasons)),
    )


def _record_selected_row(
    selected: list[ScoredLibraryRow],
    row: _LibraryRow,
    matches: Sequence[_RequirementMatchData],
    gain: float,
    newly_covered: Sequence[str],
    reasons: Sequence[str],
    best_scores: dict[str, float],
    evidence_sections: dict[str, set[str]],
    total_weight: float,
) -> None:
    total_row_score = sum(item.requirement.weight * item.score for item in matches)
    selected.append(
        ScoredLibraryRow(
            kind=row.kind,
            section_type=row.section_type,
            library_entry_id=row.library_entry_id,
            source_row_id=row.source_row_id,
            payload=row.payload,
            score=round(total_row_score, 4),
            normalized_score=round(total_row_score / total_weight, 4),
            order=row.order,
            covered_requirement_ids=tuple(newly_covered),
            selection_gain=round(gain, 4),
            selection_reasons=tuple(reasons),
        )
    )
    for match in matches:
        if match.score <= 0:
            continue
        best_scores[match.requirement.id] = max(best_scores.get(match.requirement.id, 0.0), match.score)
        if match.score >= REQUIREMENT_COVERAGE_THRESHOLD:
            evidence_sections.setdefault(match.requirement.id, set()).add(row.section_type)


def select_requirement_library_rows(
    requirements: Iterable[JobRequirement | Mapping[str, object] | str],
    library_entries: Iterable[object],
) -> list[ScoredLibraryRow]:
    """Select baseline education and then the highest-value job evidence.

    Profile is materialized by the application service. Populated education is
    selected as a baseline; every other row competes by marginal requirement
    coverage, evidence affinity, and complementary proof.
    """

    extracted = _coerce_requirements(requirements)
    rows = _library_rows(library_entries)
    if not extracted:
        return [
            ScoredLibraryRow(
                kind=row.kind,
                section_type=row.section_type,
                library_entry_id=row.library_entry_id,
                source_row_id=row.source_row_id,
                payload=row.payload,
                score=0.0,
                normalized_score=0.0,
                order=row.order,
                selection_reasons=("baseline_education",),
            )
            for row in rows
            if row.kind == "education" and row.fields
        ]

    total_weight = sum(item.weight for item in extracted) or 1.0
    row_matches = {id(row): _matches_for_library_row(extracted, row) for row in rows}
    selected: list[ScoredLibraryRow] = []
    remaining = {id(row): row for row in rows}
    best_scores: dict[str, float] = {}
    evidence_sections: dict[str, set[str]] = {}

    # Education is a stable CV baseline. Include every populated row before
    # job-specific selection and let the fitter reduce it only as a last resort.
    for row in rows:
        if row.kind != "education" or not row.fields:
            continue
        matches = row_matches[id(row)]
        _record_selected_row(
            selected,
            row,
            matches,
            0.0,
            [match.requirement.id for match in matches if match.covered],
            ("baseline_education",),
            best_scores,
            evidence_sections,
            total_weight,
        )
        remaining.pop(id(row), None)

    while remaining:
        choices: list[tuple[float, float, int, _LibraryRow, list[_RequirementMatchData], tuple[str, ...], tuple[str, ...]]] = []
        for row in remaining.values():
            matches = row_matches[id(row)]
            gain, newly_covered, reasons = _selection_value(
                row,
                matches,
                best_scores,
                evidence_sections,
                total_weight,
            )
            total_row_score = sum(item.requirement.weight * item.score for item in matches)
            if gain >= MIN_SELECTION_GAIN:
                # There is no semantic section tie-breaker. Total evidence and
                # then original Library order make equal choices reproducible.
                choices.append((gain, total_row_score, -row.order, row, matches, newly_covered, reasons))
        if not choices:
            break
        gain, _total_row_score, _order, row, matches, newly_covered, reasons = max(choices, key=lambda item: item[:3])
        _record_selected_row(
            selected,
            row,
            matches,
            gain,
            newly_covered,
            reasons,
            best_scores,
            evidence_sections,
            total_weight,
        )
        remaining.pop(id(row), None)
    return selected


def requirement_row_removal_loss(
    requirements: Iterable[JobRequirement | Mapping[str, object] | str],
    candidate: ScoredLibraryRow,
    other_rows: Iterable[ScoredLibraryRow],
) -> float:
    """Return relevance lost by removing a row from a fitted CV.

    A row that uniquely covers a required requirement is protected with an
    infinite loss. Otherwise the loss is the candidate's evidence that cannot
    be reproduced by the remaining rows.
    """

    extracted = _coerce_requirements(requirements)
    candidate_fields = _fields_for_scored_row(candidate)
    candidate_matches = [
        _match_requirement(
            requirement,
            candidate_fields,
            experience_years=_years_from_rows([candidate.payload]) if candidate.kind == "experience" else None,
        )
        for requirement in extracted
    ]
    other_matches: list[list[_RequirementMatchData]] = []
    for row in other_rows:
        fields = _fields_for_scored_row(row)
        other_matches.append(
            [
                _match_requirement(
                    requirement,
                    fields,
                    experience_years=_years_from_rows([row.payload]) if row.kind == "experience" else None,
                )
                for requirement in extracted
            ]
        )

    loss = 0.0
    for index, match in enumerate(candidate_matches):
        other_score = max((matches[index].score for matches in other_matches), default=0.0)
        if match.requirement.required and match.covered and other_score < REQUIREMENT_COVERAGE_THRESHOLD:
            return float("inf")
        loss += (
            match.requirement.weight
            * max(0.0, match.score - other_score)
            * _section_affinity(match.requirement, candidate.section_type)
        )
    return loss


def score_requirement_skill_items(
    requirements: Iterable[JobRequirement | Mapping[str, object] | str],
    row: ScoredLibraryRow,
) -> list[ScoredSkillItem]:
    """Score skill chips by the requirement weight they support."""
    if row.kind != "skill" or not isinstance(row.payload.get("items"), list):
        return []
    extracted = _coerce_requirements(requirements)
    scored: list[ScoredSkillItem] = []
    for item_index, raw_item in enumerate(row.payload["items"]):
        text = _field_text(raw_item)
        if not text:
            continue
        field = LibraryField(
            section_type="skills",
            library_entry_id=row.library_entry_id,
            source_row_id=row.source_row_id,
            field_path=f"items[{item_index}]",
            text=text,
        )
        score = sum(
            requirement.weight * _match_requirement(requirement, [field]).score
            for requirement in extracted
        )
        scored.append(
            ScoredSkillItem(
                library_entry_id=row.library_entry_id,
                source_row_id=row.source_row_id,
                item_index=item_index,
                text=text,
                score=round(score, 4),
                order=row.order,
            )
        )
    return scored


# Explicit aliases keep the service vocabulary discoverable without creating a
# second implementation or changing the versioned algorithm.
extract_job_keywords = extract_keywords
select_library_rows = select_relevant_library_rows
score_cv_relevance = calculate_relevance
extract_job_requirements = extract_requirements
calculate_requirement_relevance = evaluate_requirement_relevance
select_library_rows_by_requirements = select_requirement_library_rows


__all__ = [
    "ALGORITHM_VERSION",
    "ENTRY_RELEVANCE_THRESHOLD",
    "KEYWORD_EXTRACTION_ERROR",
    "KeywordExtractionError",
    "LibraryField",
    "MAX_FIT_PASSES",
    "MAX_KEYWORDS",
    "MAX_REQUIREMENTS",
    "REQUIREMENT_ALGORITHM_VERSION",
    "REQUIREMENT_COVERAGE_THRESHOLD",
    "ScoredLibraryRow",
    "ScoredSkillItem",
    "calculate_relevance",
    "calculate_requirement_relevance",
    "evaluate_requirement_relevance",
    "extract_job_requirements",
    "extract_requirements",
    "extract_job_keywords",
    "extract_keywords",
    "flatten_cv_fields",
    "flatten_library_entry",
    "flatten_library_fields",
    "flatten_profile_fields",
    "normalize_text",
    "score_cv_relevance",
    "score_requirement_skill_items",
    "requirement_row_removal_loss",
    "score_library_rows",
    "score_skill_items",
    "select_requirement_library_rows",
    "select_library_rows_by_requirements",
    "select_library_rows",
    "select_relevant_library_rows",
    "tokenize",
    "not_evaluated_relevance",
]
