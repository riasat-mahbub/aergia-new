"""Deterministic keyword extraction, Library matching, and CV relevance.

The ``keyword-v1`` contract is intentionally self-contained.  It performs no
network, database, renderer, subprocess, or taxonomy lookups so a saved job can
be reproduced from its input text and the user's Library snapshot.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import log2

from app.schemas.application import ExtractedKeyword, MatchEvidence, RelevanceResult

ALGORITHM_VERSION = "keyword-v1"
MAX_KEYWORDS = 30
ENTRY_RELEVANCE_THRESHOLD = 0.35
MAX_FIT_PASSES = 8

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

# These are deliberately closed.  Contact fields, dates, IDs, URLs, styles,
# booleans, and metadata never enter keyword matching.
_LIBRARY_FIELDS: dict[str, tuple[str, ...]] = {
    "education": ("institution", "degree", "gpa", "summary"),
    "skill": ("category", "items"),
    "experience": ("company", "position", "location", "description"),
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


# Explicit aliases keep the service vocabulary discoverable without creating a
# second implementation or changing the versioned algorithm.
extract_job_keywords = extract_keywords
select_library_rows = select_relevant_library_rows
score_cv_relevance = calculate_relevance


__all__ = [
    "ALGORITHM_VERSION",
    "ENTRY_RELEVANCE_THRESHOLD",
    "KEYWORD_EXTRACTION_ERROR",
    "KeywordExtractionError",
    "LibraryField",
    "MAX_FIT_PASSES",
    "MAX_KEYWORDS",
    "ScoredLibraryRow",
    "calculate_relevance",
    "extract_job_keywords",
    "extract_keywords",
    "flatten_cv_fields",
    "flatten_library_entry",
    "flatten_library_fields",
    "flatten_profile_fields",
    "normalize_text",
    "score_cv_relevance",
    "score_library_rows",
    "select_library_rows",
    "select_relevant_library_rows",
    "tokenize",
]
