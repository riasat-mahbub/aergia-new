"""Job-blind, source-grounded narrative evidence for staged tailoring."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.requirement_extractor import (
    GlinerRuntime,
    GlinerRuntimeError,
    _RawSpan,
    get_gliner_runtime,
)

CANDIDATE_EVIDENCE_SCHEMA_VERSION = "candidate-evidence-v1"
CANDIDATE_EVIDENCE_EXTRACTOR_VERSION = "gliner2.5-candidate-evidence-v1"

CANDIDATE_EVIDENCE_LABELS: dict[str, str] = {
    "evidence_claim": (
        "A minimal meaningful statement describing something the candidate actually did, created, tested, "
        "deployed, documented, investigated, improved, analyzed, researched, or was responsible for. "
        "Return the smallest independently meaningful claim supported by the text. Do not return a whole "
        "resume bullet when it contains multiple independent activities. Do not infer facts from the job."
    ),
    "technology": "A named programming language, framework, tool, platform, system, or technical method explicitly used.",
    "outcome": "An explicit result, change, delivery, or outcome of the candidate's work.",
    "quantitative_scope": "An explicit number, measure, scale, duration, or quantity associated with the work.",
    "collaboration": "An explicit collaborator, team relationship, or way the candidate worked with others.",
    "artifact": "A concrete artifact the candidate created, maintained, tested, deployed, or documented.",
    "domain": "An explicit product, industry, research, or subject-matter domain for the work.",
}

_NARRATIVE_KEYS = frozenset(
    {"description", "summary", "details", "achievements", "responsibilities", "findings", "abstract"}
)
_STRUCTURED_KEYS = frozenset(
    {
        "company", "employer", "position", "title", "name", "project", "institution", "school",
        "degree", "issuer", "certification", "language", "start_date", "end_date", "date", "current",
        "location", "url", "website", "link", "credential_url", "paper_url", "publication_date",
        "publication_value", "venue", "tech_stack", "technologies", "technology", "skills", "items",
        "category", "proficiency", "language_level", "gpa", "link_text", "paper_link_text",
    }
)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CandidateEvidenceExtractionError(ValueError):
    """The candidate evidence could not be extracted with the shared model."""


class EvidenceRelation(_StrictModel):
    kind: str
    value: str
    confidence: float = Field(ge=0, le=1)


class EvidenceProvenance(_StrictModel):
    """Internal provenance; never included in the composer projection."""

    library_entry_id: str
    library_row_id: str
    source_field: str
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_start: int = Field(ge=0)
    source_end: int = Field(ge=0)
    source_excerpt: str
    gliner_confidence: float = Field(ge=0, le=1)
    extractor_version: str


class CandidateEvidenceClaim(_StrictModel):
    id: str
    statement: str
    confidence_category: str = "explicit"
    relations: list[EvidenceRelation] = Field(default_factory=list)
    provenance: EvidenceProvenance


class CandidateEvidenceGroup(_StrictModel):
    id: str
    kind: str
    identity: dict[str, Any]
    structured_facts: dict[str, Any]
    claims: list[CandidateEvidenceClaim]


class CandidateEvidenceExtraction(_StrictModel):
    schema_version: str = CANDIDATE_EVIDENCE_SCHEMA_VERSION
    model: str
    model_revision: str
    extractor_version: str = CANDIDATE_EVIDENCE_EXTRACTOR_VERSION
    groups: list[CandidateEvidenceGroup]


class ComposerClaim(_StrictModel):
    id: str
    statement: str
    confidence_category: str
    associated_concepts: list[EvidenceRelation]


class ComposerEvidenceGroup(_StrictModel):
    id: str
    kind: str
    identity: dict[str, Any]
    structured_facts: dict[str, Any]
    claims: list[ComposerClaim]


class CandidateEvidenceProjection(_StrictModel):
    schema_version: str = CANDIDATE_EVIDENCE_SCHEMA_VERSION
    groups: list[ComposerEvidenceGroup]


def _hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _plain_text(value: Any) -> str:
    """Flatten persisted rich text without carrying formatting into inference."""

    if isinstance(value, str):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if all(isinstance(item, Mapping) and item.get("type") in {"paragraph", "bullet_list", "numbered_list"} for item in value):
            blocks: list[str] = []
            for block in value:
                items = block.get("items") or []
                lines = ["".join(_plain_text(item.get("text", "")) for item in [line] if isinstance(item, Mapping)) for line in items]
                if not lines:
                    lines = ["".join(_plain_text(item.get("text", "")) for item in items if isinstance(item, Mapping))]
                blocks.append("\n".join(line for line in lines if line.strip()))
            return "\n".join(block for block in blocks if block.strip())
        return "\n".join(part for part in (_plain_text(item) for item in value) if part.strip())
    if isinstance(value, Mapping):
        if isinstance(value.get("text"), str):
            return value["text"]
        if "root" in value:
            return _plain_text(value["root"])
        children = value.get("children")
        if isinstance(children, Sequence) and not isinstance(children, (str, bytes, bytearray)):
            return "\n".join(part for part in (_plain_text(item) for item in children) if part.strip())
    return ""


def _narrative_fields(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    fields: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            name = str(key)
            path = f"{prefix}.{name}" if prefix else name
            if name in _NARRATIVE_KEYS:
                fields.append((path, child))
            elif isinstance(child, (Mapping, list, tuple)):
                fields.extend(_narrative_fields(child, path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            fields.extend(_narrative_fields(child, f"{prefix}[{index}]"))
    return fields


def _row_id(entry_id: str, row: Mapping[str, Any], identity: Mapping[str, Any]) -> str:
    explicit = row.get("id")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    return f"row_{_hash({"entry": entry_id, "identity": identity})[:20]}"


def _identity_and_facts(row: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    identity_keys = ("company", "employer", "position", "title", "name", "project", "institution", "school")
    identity = {key: row[key] for key in identity_keys if key in row and isinstance(row[key], (str, int, float, bool, type(None)))}
    facts = {
        key: value
        for key, value in row.items()
        if key in _STRUCTURED_KEYS and key not in identity and not isinstance(value, Mapping)
    }
    return identity, facts


def _sentence_bounds(source: str, start: int, end: int) -> tuple[int, int]:
    left = 0
    right = len(source)
    for match in _SENTENCE_BOUNDARY.finditer(source):
        if match.end() <= start:
            left = match.end()
        elif match.start() >= end:
            right = match.start()
            break
    return left, right


def _associated_spans(claim: _RawSpan, all_spans: Sequence[_RawSpan], source: str) -> list[_RawSpan]:
    if claim.start is None or claim.end is None:
        return []
    bounds = _sentence_bounds(source, claim.start, claim.end)
    concepts = [
        span for span in all_spans
        if span.label != "evidence_claim" and span.start is not None and span.end is not None
        and span.start >= bounds[0] and span.end <= bounds[1]
    ]
    return concepts


def _claim_identifier(entry_id: str, row_id: str, field_name: str, statement: str) -> str:
    return f"claim_{_hash([entry_id, row_id, field_name, _normalized(statement)])[:24]}"


class CandidateEvidenceExtractor:
    """Extract narrative facts from Library entries without job context."""

    def __init__(self, runtime: GlinerRuntime | None = None) -> None:
        self.runtime = runtime or get_gliner_runtime()

    def extract(self, library: Sequence[Mapping[str, Any]]) -> CandidateEvidenceExtraction:
        groups: list[CandidateEvidenceGroup] = []
        model_version = f"{self.runtime.model_name}@{self.runtime.revision or 'default'}"
        for entry in library:
            entry_id = str(entry.get("id") or "")
            kind = str(entry.get("kind") or "other")
            payload = entry.get("payload")
            rows = [row for row in payload if isinstance(row, Mapping)] if isinstance(payload, list) else []
            for row in rows:
                identity, structured = _identity_and_facts(row)
                row_id = _row_id(entry_id, row, identity)
                group_id = f"source_{_hash([entry_id, row_id])[:20]}"
                claims_by_key: dict[str, CandidateEvidenceClaim] = {}
                for field_path, raw_value in _narrative_fields(row):
                    source = _plain_text(raw_value)
                    if not source.strip():
                        continue
                    source_hash = _hash(raw_value)
                    try:
                        spans = self.runtime.extract_entities(source, CANDIDATE_EVIDENCE_LABELS)
                    except GlinerRuntimeError as exc:
                        raise CandidateEvidenceExtractionError("Unable to extract candidate evidence") from exc
                    narrative_spans = [
                        span for span in spans
                        if span.label == "evidence_claim" and span.text.strip()
                        and span.start is not None and span.end is not None
                        and source[span.start:span.end].strip()
                    ]
                    for span in narrative_spans:
                        start, end = span.start or 0, span.end or 0
                        statement = source[start:end].strip()
                        claim_key = _claim_identifier(entry_id, row_id, field_path.rsplit(".", 1)[-1], statement)
                        related = _associated_spans(span, spans, source)
                        relations = {
                            (item.label, _normalized(item.text)): EvidenceRelation(
                                kind=item.label,
                                value=item.text.strip(),
                                confidence=item.confidence,
                            )
                            for item in related
                            if item.text.strip()
                        }
                        provenance = EvidenceProvenance(
                            library_entry_id=entry_id,
                            library_row_id=row_id,
                            source_field=field_path,
                            source_hash=source_hash,
                            source_start=start,
                            source_end=end,
                            source_excerpt=source[start:end],
                            gliner_confidence=span.confidence,
                            extractor_version=f"{CANDIDATE_EVIDENCE_EXTRACTOR_VERSION}:{model_version}",
                        )
                        claim = CandidateEvidenceClaim(
                            id=claim_key,
                            statement=statement,
                            relations=sorted(relations.values(), key=lambda item: (item.kind, item.value.casefold())),
                            provenance=provenance,
                        )
                        claims_by_key.setdefault(claim_key, claim)
                groups.append(
                    CandidateEvidenceGroup(
                        id=group_id,
                        kind=kind,
                        identity=identity,
                        structured_facts=structured,
                        claims=sorted(claims_by_key.values(), key=lambda item: item.id),
                    )
                )
        return CandidateEvidenceExtraction(
            model=self.runtime.model_name,
            model_revision=self.runtime.revision or "default",
            groups=sorted(groups, key=lambda item: item.id),
        )


def composer_projection(extraction: CandidateEvidenceExtraction) -> CandidateEvidenceProjection:
    """Drop source offsets, excerpts, Library IDs, and source ordering."""

    groups = [
        ComposerEvidenceGroup(
            id=group.id,
            kind=group.kind,
            identity=group.identity,
            structured_facts=group.structured_facts,
            claims=[
                ComposerClaim(
                    id=claim.id,
                    statement=claim.statement,
                    confidence_category=claim.confidence_category,
                    associated_concepts=claim.relations,
                )
                for claim in sorted(group.claims, key=lambda item: item.id)
            ],
        )
        for group in sorted(extraction.groups, key=lambda item: item.id)
    ]
    return CandidateEvidenceProjection(groups=groups)


def validate_provenance(extraction: CandidateEvidenceExtraction, sources: Mapping[tuple[str, str], str]) -> None:
    """Raise when an internal claim cannot be resolved to its exact source span."""

    for group in extraction.groups:
        for claim in group.claims:
            provenance = claim.provenance
            source = sources.get((provenance.library_entry_id, provenance.source_field))
            if source is None:
                raise ValueError(f"orphan candidate evidence claim: {claim.id}")
            if source[provenance.source_start:provenance.source_end] != provenance.source_excerpt:
                raise ValueError(f"candidate evidence source span mismatch: {claim.id}")


__all__ = [
    "CANDIDATE_EVIDENCE_EXTRACTOR_VERSION",
    "CANDIDATE_EVIDENCE_LABELS",
    "CANDIDATE_EVIDENCE_SCHEMA_VERSION",
    "CandidateEvidenceExtractionError",
    "CandidateEvidenceExtraction",
    "CandidateEvidenceExtractor",
    "CandidateEvidenceProjection",
    "composer_projection",
    "validate_provenance",
]
