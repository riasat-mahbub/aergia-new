"""Standalone GLiNER2.5 requirement-extraction spike primitives.

This module is intentionally not imported by the application.  It exists to
answer one question before production integration: can a small local
GLiNER2.5 checkpoint identify better requirement spans than requirement-v2
within the application's deployment budget?

The prototype keeps semantic extraction, deterministic enrichment, and the
comparison adapter separate.  It does not know about CVs, Library entries,
rendering, or HTTP persistence.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class Importance(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Constraint:
    """A structured constraint attached to the source requirement."""

    kind: str
    value: int | str | None
    source_text: str

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "value": self.value, "source_text": self.source_text}


@dataclass(frozen=True, slots=True)
class Requirement:
    """The proposed internal requirement contract used by the spike."""

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

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_text": self.source_text,
            "source_start": self.source_start,
            "source_end": self.source_end,
            "type": self.type,
            "importance": self.importance.value,
            "concepts": list(self.concepts),
            "constraints": [constraint.as_dict() for constraint in self.constraints],
            "confidence": self.confidence,
            "extractor": self.extractor,
            "extractor_version": self.extractor_version,
        }


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """A complete extraction result plus enough metadata for benchmarking."""

    requirements: tuple[Requirement, ...]
    extractor: str
    extractor_version: str
    status: str = "primary"
    source_hash: str = ""
    warnings: tuple[str, ...] = ()
    inference_path: str = "short"

    def as_dict(self) -> dict[str, Any]:
        return {
            "requirements": [requirement.as_dict() for requirement in self.requirements],
            "extractor": self.extractor,
            "extractor_version": self.extractor_version,
            "status": self.status,
            "source_hash": self.source_hash,
            "warnings": list(self.warnings),
            "inference_path": self.inference_path,
        }


class EntityModel(Protocol):
    """Small protocol used by tests to avoid loading a model checkpoint."""

    def extract_entities(self, text: str, labels: Mapping[str, str], **kwargs: Any) -> Mapping[str, Any]: ...

    def extract_entities_long(
        self,
        text: str,
        labels: Mapping[str, str],
        **kwargs: Any,
    ) -> Mapping[str, Any]: ...


MODEL_LABELS: dict[str, str] = {
    "candidate_requirement": (
        "A complete sentence or bullet from a job posting stating what a candidate must, should, or will be able "
        "to do. Include implicit requirements expressed as responsibilities, such as owning production services. "
        "Return the whole sentence or bullet. Do not return section headings, company descriptions, or isolated "
        "technology names."
    ),
    "skill": "A named technical skill, tool, programming language, platform, or method expected from a candidate.",
    "competency": "A professional or interpersonal competency expected from a candidate.",
    "experience_expectation": "A statement about experience, ownership, seniority, or work performed by a candidate.",
    "education_requirement": "An education, degree, academic, or study requirement for a candidate.",
    "certification_requirement": "A professional certification, license, or credential expected from a candidate.",
    "domain_knowledge": "A domain, industry, or subject-matter knowledge requirement for a candidate.",
}

_LABEL_TYPE: dict[str, str] = {
    "skill": "hard_skill",
    "competency": "responsibility",
    "experience_expectation": "quantitative",
    "education_requirement": "education",
    "certification_requirement": "certification",
    "domain_knowledge": "other",
}
_REQUIREMENT_LABELS = frozenset({"requirement", "candidate_requirement"})
_CONCEPT_LABELS = frozenset(_LABEL_TYPE)

_REQUIRED_RE = re.compile(
    r"\b(?:must(?:\s+have)?|required|required qualifications?|mandatory|essential|shall)\b",
    re.IGNORECASE,
)
_PREFERRED_RE = re.compile(
    r"\b(?:preferred|preferably|nice\s+to\s+have|a\s+plus|bonus|desirable|advantageous)\b",
    re.IGNORECASE,
)
_NEGATED_RE = re.compile(
    r"\b(?:not\s+required|not\s+necessary|not\s+mandatory|optional|no\s+.+?\s+required)\b",
    re.IGNORECASE,
)
_YEARS_RE = re.compile(
    r"\b(?:(?:at\s+least|minimum\s+of|min(?:imum)?|more\s+than)\s+)?"
    r"(?P<number>\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten)\+?\s+"
    r"(?P<unit>years?|yrs?)\b",
    re.IGNORECASE,
)
_DEGREE_RE = re.compile(
    r"\b(?:ph\.?d\.?|doctorate|doctoral|master(?:'|’)s?|m\.?s\.?|mba|"
    r"bachelor(?:'|’)s?|b\.?s\.?|b\.?a\.?|associate(?:'|’)s?|a\.?a\.?)\b",
    re.IGNORECASE,
)
_CERTIFICATION_RE = re.compile(
    r"\b(?:certification|certificate|certified|license|licensed|credential)\b",
    re.IGNORECASE,
)
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

_HEADING_RE = re.compile(
    r"(?:^|\b)(?:minimum|basic|required|preferred|desired|nice\s+to\s+have|"
    r"qualifications?|requirements?|responsibilities|what\s+you(?:'|’)ll\s+do|"
    r"what\s+you\s+will\s+do|must\s+have|bonus)(?:\b|$)",
    re.IGNORECASE,
)
_HEADING_TEXT_RE = re.compile(
    r"^(?:(?:minimum|basic|required|preferred|desired)\s+)?(?:qualifications?|requirements?|skills?)$|"
    r"^(?:responsibilities|must\s+have|nice\s+to\s+have|bonus|"
    r"what\s+you(?:'|’)ll\s+do|what\s+you\s+will\s+do)$",
    re.IGNORECASE,
)


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


def _source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalise(value: str) -> str:
    return " ".join(value.casefold().split())


def _coerce_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


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


def _coerce_raw_spans(source: str, result: Mapping[str, Any]) -> list[_RawSpan]:
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

            start: int | None
            end: int | None
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
            resolved_text = source[start:end] if start is not None and end is not None else str(raw_text).strip()
            spans.append(
                _RawSpan(
                    label=str(label),
                    text=resolved_text,
                    start=start,
                    end=end,
                    confidence=_coerce_confidence(confidence),
                )
            )
    return spans


def _overlap(left: _RawSpan, right: _RawSpan) -> int:
    if left.start is None or left.end is None or right.start is None or right.end is None:
        return 0
    return max(0, min(left.end, right.end) - max(left.start, right.start))


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
        duplicate_index: int | None = None
        for index, existing in enumerate(kept):
            if candidate.label != existing.label:
                continue
            if _normalise(candidate.text) == _normalise(existing.text):
                duplicate_index = index
                break
            overlap = _overlap(candidate, existing)
            candidate_length = max(1, (candidate.end or 0) - (candidate.start or 0))
            existing_length = max(1, (existing.end or 0) - (existing.start or 0))
            if overlap and overlap / min(candidate_length, existing_length) >= 0.8:
                duplicate_index = index
                break
        if duplicate_index is None:
            kept.append(candidate)
            continue
        existing = kept[duplicate_index]
        candidate_length = max(1, (candidate.end or 0) - (candidate.start or 0))
        existing_length = max(1, (existing.end or 0) - (existing.start or 0))
        if (
            candidate.start is not None
            and candidate.end is not None
            and existing.start is not None
            and existing.end is not None
        ):
            start = min(candidate.start, existing.start)
            end = max(candidate.end, existing.end)
            text = candidate.text if candidate_length >= existing_length else existing.text
        else:
            start, end, text = existing.start, existing.end, existing.text
        kept[duplicate_index] = _RawSpan(
            label=existing.label,
            text=text,
            start=start,
            end=end,
            confidence=max(candidate.confidence, existing.confidence),
        )
    return kept


def _source_units(source: str) -> list[_SourceUnit]:
    units: list[_SourceUnit] = []
    for match in re.finditer(r"[^\n]+", source):
        start, end = match.span()
        text = match.group(0).strip()
        leading = len(match.group(0)) - len(match.group(0).lstrip())
        trailing = len(match.group(0).rstrip())
        start += leading
        end = match.start() + trailing
        if text:
            units.append(_SourceUnit(start=start, end=end, text=source[start:end]))
    if units:
        return units
    return [_SourceUnit(start=0, end=len(source), text=source)] if source else []


def _unit_for_span(source: str, span: _RawSpan) -> _SourceUnit | None:
    if span.start is None:
        return None
    for unit in _source_units(source):
        if unit.start <= span.start < unit.end:
            return unit
    return None


def _heading_for_offset(source: str, offset: int | None) -> str:
    if offset is None:
        return ""
    heading = ""
    for unit in _source_units(source):
        if unit.start > offset:
            break
        if _is_heading_text(unit.text):
            heading = unit.text.strip(" -*\t")
    return heading


def _is_heading_text(value: str) -> bool:
    stripped = value.strip(" -*\t")
    return (
        len(stripped) <= 80
        and len(stripped.split()) <= 10
        and not re.search(r"[.!?]$", stripped)
        and bool(_HEADING_TEXT_RE.fullmatch(stripped))
    )


def _trim_heading_from_span(source: str, span: _RawSpan) -> _RawSpan:
    """Remove a heading accidentally included in a model span when unambiguous."""

    if span.start is None or span.end is None:
        return span
    units = [
        unit
        for unit in _source_units(source)
        if _overlap(span, _RawSpan("unit", unit.text, unit.start, unit.end, 0.0))
    ]
    non_headings = [unit for unit in units if not _is_heading_text(unit.text)]
    if len(units) > 1 and len(non_headings) == 1:
        unit = non_headings[0]
        return _RawSpan(
            label=span.label,
            text=unit.text,
            start=unit.start,
            end=unit.end,
            confidence=span.confidence,
        )
    return span


def _importance(source_text: str, heading: str) -> Importance:
    if _NEGATED_RE.search(source_text):
        return Importance.UNKNOWN
    if _REQUIRED_RE.search(source_text):
        return Importance.REQUIRED
    if _PREFERRED_RE.search(source_text):
        return Importance.PREFERRED
    heading_folded = heading.casefold()
    if any(term in heading_folded for term in ("preferred", "desired", "nice", "bonus")):
        return Importance.PREFERRED
    if any(term in heading_folded for term in ("required", "minimum", "basic", "must", "qualification", "requirement")):
        return Importance.REQUIRED
    return Importance.UNKNOWN


def _integer(value: str) -> int:
    value_folded = value.casefold()
    return int(value) if value.isdigit() else _WORD_NUMBERS[value_folded]


def _constraints(source_text: str, context_text: str, label: str) -> tuple[Constraint, ...]:
    constraints: list[Constraint] = []
    for match in _YEARS_RE.finditer(context_text):
        try:
            minimum = _integer(match.group("number"))
        except (KeyError, ValueError):
            continue
        constraints.append(
            Constraint(
                kind="years_experience",
                value=minimum,
                source_text=context_text[match.start() : match.end()],
            )
        )
        break
    degree = _DEGREE_RE.search(context_text)
    if degree:
        value = degree.group(0).casefold().replace("’", "'")
        if "ph" in value or "doctor" in value:
            level = "doctorate"
        elif "master" in value or value in {"m.s.", "ms", "mba"}:
            level = "master"
        elif "bachelor" in value or value in {"b.s.", "bs", "b.a.", "ba"}:
            level = "bachelor"
        else:
            level = "associate"
        constraints.append(
            Constraint(kind="degree_level", value=level, source_text=context_text[degree.start() : degree.end()])
        )
    if label == "certification_requirement" or _CERTIFICATION_RE.search(context_text):
        marker = _CERTIFICATION_RE.search(context_text)
        if marker:
            constraints.append(
                Constraint(
                    kind="certification",
                    value="mentioned",
                    source_text=context_text[marker.start() : marker.end()],
                )
            )
    # The argument is retained to make it explicit that constraints are
    # attached to a model candidate, while the full source line supplies
    # deterministic context when the model span is only a phrase.
    del source_text
    unique: dict[tuple[str, str], Constraint] = {}
    for constraint in constraints:
        unique[(constraint.kind, str(constraint.value))] = constraint
    return tuple(unique.values())


def _taxonomy_concepts(text: str) -> list[tuple[str, str]]:
    """Return canonical taxonomy concepts found with conservative boundaries."""

    try:
        from app.services.relevance_taxonomy import ALIAS_TO_CANONICAL, TAXONOMY
    except ImportError:
        return []
    found: list[tuple[str, str]] = []
    folded = text.casefold()
    for alias, canonical in sorted(ALIAS_TO_CANONICAL.items(), key=lambda item: (-len(item[0]), item[0])):
        pattern = rf"(?<![\w]){re.escape(alias)}(?![\w])"
        if re.search(pattern, folded):
            found.append((canonical, TAXONOMY[canonical][0]))
    deduped: dict[str, str] = {}
    for canonical, kind in found:
        deduped[canonical] = kind
    return list(deduped.items())


def _requirement_type(label: str, concepts: Sequence[tuple[str, str]], constraints: Sequence[Constraint]) -> str:
    if any(constraint.kind == "degree_level" for constraint in constraints):
        return "education"
    if any(constraint.kind == "certification" for constraint in constraints):
        return "certification"
    if any(constraint.kind == "years_experience" for constraint in constraints):
        return "quantitative"
    if label in _LABEL_TYPE:
        return _LABEL_TYPE[label]
    if concepts:
        return concepts[0][1]
    return "other"


def _concept_values(model_spans: Iterable[_RawSpan], source_text: str) -> tuple[str, ...]:
    values: list[str] = []
    for span in model_spans:
        value = _normalise(span.text)
        if value and value not in values:
            values.append(value)
    for canonical, _kind in _taxonomy_concepts(source_text):
        if canonical not in values:
            values.append(canonical)
    return tuple(values)


def _span_intersects(left: _RawSpan, right: _RawSpan) -> bool:
    return _overlap(left, right) > 0


def requirements_from_model_output(
    source: str,
    result: Mapping[str, Any],
    *,
    extractor: str = "gliner2",
    extractor_version: str = "gliner2.5-spike",
    inference_path: str = "short",
) -> ExtractionResult:
    """Convert GLiNER2 entity output into the standalone contract."""

    raw_spans = _coerce_raw_spans(source, result)
    requirement_spans = _dedupe_spans(span for span in raw_spans if span.label in _REQUIREMENT_LABELS)
    concept_spans = [span for span in raw_spans if span.label in _CONCEPT_LABELS]

    if not requirement_spans:
        # Some zero-shot prompts return only typed concepts.  Turn each
        # concept's containing bullet into a candidate, but retain the lower
        # confidence and provenance so this behavior is visible in evaluation.
        candidates: list[_RawSpan] = []
        for span in concept_spans:
            unit = _unit_for_span(source, span)
            if unit:
                candidates.append(
                    _RawSpan(
                        label="requirement",
                        text=unit.text,
                        start=unit.start,
                        end=unit.end,
                        confidence=span.confidence,
                    )
                )
        requirement_spans = _dedupe_spans(candidates)

    requirements: list[Requirement] = []
    for index, raw_candidate in enumerate(
        sorted(requirement_spans, key=lambda span: (span.start or 10**12, span.end or 10**12)), 1
    ):
        candidate = _trim_heading_from_span(source, raw_candidate)
        if _is_heading_text(candidate.text):
            continue
        candidate_source = candidate.text
        unit = _unit_for_span(source, candidate)
        context_text = unit.text if unit else candidate_source
        heading = _heading_for_offset(source, candidate.start)
        attached_model_spans = [
            span for span in concept_spans if _span_intersects(candidate, span) or (unit and _span_intersects(span, _RawSpan("unit", unit.text, unit.start, unit.end, 0.0)))
        ]
        taxonomy = _taxonomy_concepts(context_text)
        constraints = _constraints(candidate_source, context_text, candidate.label)
        concepts = _concept_values(attached_model_spans, context_text)
        requirement_type = _requirement_type(candidate.label, taxonomy, constraints)
        if not concepts and taxonomy:
            concepts = tuple(canonical for canonical, _kind in taxonomy)
        requirements.append(
            Requirement(
                id=f"req-{index:03d}",
                source_text=candidate_source,
                source_start=candidate.start,
                source_end=candidate.end,
                type=requirement_type,
                importance=_importance(candidate_source, heading),
                concepts=concepts,
                constraints=constraints,
                confidence=candidate.confidence,
                extractor=extractor,
                extractor_version=extractor_version,
            )
        )
    return ExtractionResult(
        requirements=tuple(requirements),
        extractor=extractor,
        extractor_version=extractor_version,
        source_hash=_source_hash(source),
        inference_path=inference_path,
    )


class Gliner2RequirementExtractor:
    """Lazy GLiNER2.5 adapter used only by the spike CLI."""

    def __init__(
        self,
        *,
        model_name: str = "fastino/gliner2.5-small-v1",
        revision: str | None = None,
        chunk_size: int = 384,
        chunk_overlap: int = 64,
        model: EntityModel | None = None,
    ) -> None:
        self.model_name = model_name
        self.revision = revision
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._model = model
        self.last_inference_path = "short"

    def load(self) -> EntityModel:
        if self._model is None:
            try:
                from gliner2 import AutoExtractor
            except ImportError as exc:  # pragma: no cover - exercised by CLI without optional deps
                raise RuntimeError(
                    "GLiNER2 local inference is not installed; install gliner2[local] to run the spike"
                ) from exc
            kwargs: dict[str, Any] = {}
            if self.revision:
                kwargs["revision"] = self.revision
            self._model = AutoExtractor.from_pretrained(self.model_name, **kwargs)
        return self._model

    @property
    def model(self) -> EntityModel:
        return self.load()

    def extract(self, source: str) -> ExtractionResult:
        model = self.load()
        word_count = len(re.findall(r"\S+", source))
        labels = MODEL_LABELS
        if word_count > self.chunk_size:
            method = getattr(model, "extract_entities_long", None)
            if method is None:
                raise RuntimeError("loaded GLiNER2 model does not expose extract_entities_long")
            self.last_inference_path = "long"
            raw = method(
                source,
                labels,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                include_confidence=True,
                include_spans=True,
                overlap_policy="flat",
            )
        else:
            self.last_inference_path = "short"
            raw = model.extract_entities(
                source,
                labels,
                include_confidence=True,
                include_spans=True,
                overlap_policy="flat",
            )
        return requirements_from_model_output(
            source,
            raw,
            extractor="gliner2",
            extractor_version=f"{self.model_name}@{self.revision or 'default'}",
            inference_path=self.last_inference_path,
        )


def _locate_requirement(source: str, text: str, normalized: str) -> tuple[str, int | None, int | None]:
    for needle in (text, normalized):
        start, end = _find_text_span(source, needle)
        if start is not None and end is not None:
            return source[start:end], start, end
    for unit in _source_units(source):
        if _normalise(normalized) and _normalise(normalized) in _normalise(unit.text):
            return unit.text, unit.start, unit.end
    return text, None, None


def existing_v2_requirements(source: str, *, role: str = "") -> ExtractionResult:
    """Adapt the former deterministic requirement-v2 result without changing it."""

    try:
        from app.services.relevance import extract_requirements_v2
    except ImportError as exc:  # pragma: no cover - script always runs with api on sys.path
        raise RuntimeError("run the spike with the api package on PYTHONPATH") from exc
    extracted = extract_requirements_v2(role, source)
    requirements: list[Requirement] = []
    for index, item in enumerate(extracted, 1):
        item_text = str(getattr(item, "text", ""))
        normalized = str(getattr(item, "normalized", item_text))
        source_text, start, end = _locate_requirement(source, item_text, normalized)
        raw_constraint = getattr(item, "constraint", None) or {}
        constraints: list[Constraint] = []
        if isinstance(raw_constraint, Mapping):
            kind = raw_constraint.get("kind")
            if kind:
                value = raw_constraint.get("minimum", raw_constraint.get("degree_level", raw_constraint.get("value")))
                constraints.append(Constraint(kind=str(kind), value=value, source_text=source_text))
        required = bool(getattr(item, "required", False))
        requirements.append(
            Requirement(
                id=f"v2-{getattr(item, 'id', f'req-{index:03d}')}",
                source_text=source_text,
                source_start=start,
                source_end=end,
                type=str(getattr(item, "type", "other")),
                importance=Importance.REQUIRED if required else Importance.PREFERRED,
                concepts=(str(getattr(item, "canonical", None) or normalized),),
                constraints=tuple(constraints),
                confidence=1.0,
                extractor="requirement-v2",
                extractor_version="requirement-v2",
            )
        )
    return ExtractionResult(
        requirements=tuple(requirements),
        extractor="requirement-v2",
        extractor_version="requirement-v2",
        source_hash=_source_hash(source),
    )


def _requirement_similarity(left: Requirement, right: Requirement) -> float:
    if left.source_start is not None and left.source_end is not None and right.source_start is not None and right.source_end is not None:
        overlap = max(0, min(left.source_end, right.source_end) - max(left.source_start, right.source_start))
        shorter = max(1, min(left.source_end - left.source_start, right.source_end - right.source_start))
        if overlap / shorter >= 0.5:
            return 1.0
    left_text = _normalise(left.source_text)
    right_text = _normalise(right.source_text)
    if left_text and (left_text in right_text or right_text in left_text):
        return 0.9
    left_concepts = set(left.concepts)
    right_concepts = set(right.concepts)
    if left_concepts and right_concepts:
        overlap = len(left_concepts & right_concepts) / len(left_concepts | right_concepts)
        if overlap:
            return 0.5 + 0.4 * overlap
    return 0.0


def merge_requirement_sets(*results: ExtractionResult) -> ExtractionResult:
    """Merge semantic and deterministic results for comparison only."""

    merged: list[Requirement] = []
    for result in results:
        for incoming in result.requirements:
            match_index: int | None = None
            for index, existing in enumerate(merged):
                if _requirement_similarity(existing, incoming) >= 0.5:
                    match_index = index
                    break
            if match_index is None:
                merged.append(incoming)
                continue
            existing = merged[match_index]
            deterministic = incoming.extractor == "requirement-v2"
            if deterministic and incoming.importance != Importance.UNKNOWN:
                importance = incoming.importance
            elif existing.importance != Importance.UNKNOWN:
                importance = existing.importance
            else:
                importance = incoming.importance
            constraints = incoming.constraints if deterministic and incoming.constraints else existing.constraints or incoming.constraints
            concepts = tuple(dict.fromkeys((*existing.concepts, *incoming.concepts)))
            if existing.source_start is not None and incoming.source_start is not None:
                source_start = min(existing.source_start, incoming.source_start)
                source_end = max(existing.source_end or existing.source_start, incoming.source_end or incoming.source_start)
                source_text = existing.source_text if len(existing.source_text) >= len(incoming.source_text) else incoming.source_text
            else:
                source_start, source_end, source_text = existing.source_start, existing.source_end, existing.source_text
            merged[match_index] = Requirement(
                id=existing.id,
                source_text=source_text,
                source_start=source_start,
                source_end=source_end,
                type=existing.type if existing.type != "other" else incoming.type,
                importance=importance,
                concepts=concepts,
                constraints=constraints,
                confidence=max(existing.confidence, incoming.confidence),
                extractor="hybrid" if existing.extractor != incoming.extractor else existing.extractor,
                extractor_version=f"{existing.extractor_version}+{incoming.extractor_version}"
                if existing.extractor_version != incoming.extractor_version
                else existing.extractor_version,
            )
    normalized = tuple(
        Requirement(
            id=f"req-{index:03d}",
            source_text=item.source_text,
            source_start=item.source_start,
            source_end=item.source_end,
            type=item.type,
            importance=item.importance,
            concepts=item.concepts,
            constraints=item.constraints,
            confidence=item.confidence,
            extractor=item.extractor,
            extractor_version=item.extractor_version,
        )
        for index, item in enumerate(sorted(merged, key=lambda item: (item.source_start or 10**12, item.source_end or 10**12)), 1)
    )
    return ExtractionResult(
        requirements=normalized,
        extractor="hybrid",
        extractor_version="gliner2+requirement-v2",
        source_hash=results[0].source_hash if results else "",
    )


def compare_requirement_sets(baseline: Sequence[Requirement], candidate: Sequence[Requirement]) -> dict[str, Any]:
    """Produce a small human-readable diff between two extraction results."""

    pair_scores: list[tuple[float, int, int]] = []
    for baseline_index, left in enumerate(baseline):
        for candidate_index, right in enumerate(candidate):
            score = _requirement_similarity(left, right)
            if score >= 0.5:
                pair_scores.append((score, baseline_index, candidate_index))
    pair_scores.sort(reverse=True)
    matched_baseline: set[int] = set()
    matched_candidate: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for _score, baseline_index, candidate_index in pair_scores:
        if baseline_index in matched_baseline or candidate_index in matched_candidate:
            continue
        matched_baseline.add(baseline_index)
        matched_candidate.add(candidate_index)
        pairs.append((baseline_index, candidate_index))

    def summary(item: Requirement) -> dict[str, Any]:
        return {
            "source_text": item.source_text,
            "importance": item.importance.value,
            "concepts": list(item.concepts),
            "constraints": [constraint.as_dict() for constraint in item.constraints],
        }

    importance_changed = [
        {"baseline": summary(baseline[left]), "candidate": summary(candidate[right])}
        for left, right in pairs
        if baseline[left].importance != candidate[right].importance
    ]
    constraint_changed = [
        {"baseline": summary(baseline[left]), "candidate": summary(candidate[right])}
        for left, right in pairs
        if tuple(constraint.as_dict() for constraint in baseline[left].constraints)
        != tuple(constraint.as_dict() for constraint in candidate[right].constraints)
    ]
    split = []
    for baseline_index, item in enumerate(baseline):
        matched = [candidate[index] for index in range(len(candidate)) if _requirement_similarity(item, candidate[index]) >= 0.5]
        if len(matched) > 1:
            split.append({"baseline": summary(item), "candidate_parts": [summary(value) for value in matched]})
    merge = []
    for candidate_index, item in enumerate(candidate):
        matched = [baseline[index] for index in range(len(baseline)) if _requirement_similarity(baseline[index], item) >= 0.5]
        if len(matched) > 1:
            merge.append({"candidate": summary(item), "baseline_parts": [summary(value) for value in matched]})
    return {
        "added": [summary(candidate[index]) for index in range(len(candidate)) if index not in matched_candidate],
        "removed": [summary(baseline[index]) for index in range(len(baseline)) if index not in matched_baseline],
        "importance_changed": importance_changed,
        "constraint_changed": constraint_changed,
        "split": split,
        "merged": merge,
    }


__all__ = [
    "Constraint",
    "EntityModel",
    "ExtractionResult",
    "Gliner2RequirementExtractor",
    "Importance",
    "MODEL_LABELS",
    "Requirement",
    "compare_requirement_sets",
    "existing_v2_requirements",
    "merge_requirement_sets",
    "requirements_from_model_output",
]
