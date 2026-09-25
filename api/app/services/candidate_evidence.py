"""Validation and projection for source-granular candidate semantics."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CANDIDATE_EVIDENCE_SCHEMA_VERSION = "candidate-semantic-v1"
CANDIDATE_EVIDENCE_EXTRACTOR_VERSION = "isolated-propositions-v1"
CANDIDATE_EVIDENCE_PROMPT_VERSION = "candidate-proposition-prompt-v7"
CANDIDATE_EVIDENCE_PROPOSITION_MODEL = "isolated-worker"
CANDIDATE_EVIDENCE_PROPOSITION_MODEL_REVISION = "contract-managed"
MAX_PROPOSITION_EXCERPT_CHARACTERS = 250

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
_IDENTITY_KEYS = ("company", "employer", "position", "title", "name", "project", "institution", "school")
_ALLOWED_CONCEPT_KINDS = frozenset(
    {"technology", "method", "collaborator", "artifact", "domain", "outcome", "scope", "other"}
)
_ALLOWED_RELATIONS = frozenset(
    {"used", "deployed_with", "tested_with", "tested_across", "collaborated_with", "created", "documented", "within", "associated_with"}
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CandidateEvidenceExtractionError(ValueError):
    """Candidate evidence could not be validated against its authoritative source."""


class EvidenceRelation(_StrictModel):
    kind: Literal["technology", "method", "collaborator", "artifact", "domain", "outcome", "scope", "other"]
    value: str = Field(min_length=1, max_length=160)
    relation: Literal[
        "used", "deployed_with", "tested_with", "tested_across", "collaborated_with",
        "created", "documented", "within", "associated_with",
    ]


class EvidenceProvenance(_StrictModel):
    """Internal provenance; never included in the composer projection."""

    library_entry_id: str
    library_row_id: str
    source_field: str
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_start: int = Field(ge=0)
    source_end: int = Field(gt=0)
    source_excerpt: str = Field(min_length=1, max_length=MAX_PROPOSITION_EXCERPT_CHARACTERS)
    extractor_version: str


class CandidateEvidenceClaim(_StrictModel):
    id: str
    statement: str = Field(min_length=3, max_length=280)
    confidence_category: Literal["explicit"] = "explicit"
    relations: list[EvidenceRelation] = Field(default_factory=list)
    provenance: EvidenceProvenance


class CandidateEvidenceGroup(_StrictModel):
    id: str
    kind: str
    identity: dict[str, Any]
    structured_facts: dict[str, Any]
    claims: list[CandidateEvidenceClaim]


class CandidateEvidenceExtraction(_StrictModel):
    schema_version: Literal["candidate-semantic-v1"] = CANDIDATE_EVIDENCE_SCHEMA_VERSION
    proposition_extractor: Literal["isolated-job-blind-worker"] = "isolated-job-blind-worker"
    proposition_model: str = CANDIDATE_EVIDENCE_PROPOSITION_MODEL
    proposition_model_revision: str = CANDIDATE_EVIDENCE_PROPOSITION_MODEL_REVISION
    prompt_version: str = CANDIDATE_EVIDENCE_PROMPT_VERSION
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
    schema_version: Literal["candidate-evidence-v2"] = "candidate-evidence-v2"
    groups: list[ComposerEvidenceGroup]


@dataclass(frozen=True)
class CandidateEvidenceSource:
    source_id: str
    entry_id: str
    row_id: str
    kind: str
    identity: dict[str, Any]
    structured_facts: dict[str, Any]
    source_field: str
    source_hash: str
    raw_value: Any
    text: str
    canonical_skills: list[str] = field(default_factory=list)


def _hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _plain_text(value: Any) -> str:
    """Flatten persisted rich text while keeping exact offsets in the flattened source."""

    if isinstance(value, str):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if all(isinstance(item, Mapping) and item.get("type") in {"paragraph", "bullet_list", "numbered_list"} for item in value):
            blocks: list[str] = []
            for block in value:
                items = block.get("items") or []
                lines = [
                    "".join(_plain_text(line.get("text", "")) for line in [item] if isinstance(line, Mapping))
                    for item in items
                ]
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


def _row_id(
    entry_id: str,
    row: Mapping[str, Any],
    index: int,
    persisted_ids: Sequence[Any] = (),
) -> str:
    if index < len(persisted_ids) and isinstance(persisted_ids[index], str) and persisted_ids[index].strip():
        return persisted_ids[index].strip()
    explicit = row.get("id")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    # Legacy, not-yet-backfilled callers get an identity independent of mutable
    # row contents. The persistent index writes a UUID before exposing sources.
    return f"legacy_{_hash([entry_id, index])[:20]}"


def _identity_and_facts(row: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    identity = {
        key: row[key]
        for key in _IDENTITY_KEYS
        if key in row and isinstance(row[key], (str, int, float, bool, type(None)))
    }
    facts = {
        key: value
        for key, value in row.items()
        if key in _STRUCTURED_KEYS and key not in identity and not isinstance(value, Mapping)
    }
    return identity, facts


def iter_candidate_sources(library: Sequence[Mapping[str, Any]]) -> list[CandidateEvidenceSource]:
    """Flatten narrative fields into order-independent, opaque source handles."""

    sources: list[CandidateEvidenceSource] = []
    for entry in library:
        entry_id = str(entry.get("id") or "")
        kind = str(entry.get("kind") or "other")
        payload = entry.get("payload")
        rows = [row for row in payload if isinstance(row, Mapping)] if isinstance(payload, list) else []
        persisted_ids = entry.get("_row_ids") or entry.get("row_ids") or []
        for index, row in enumerate(rows):
            identity, structured = _identity_and_facts(row)
            row_id = _row_id(entry_id, row, index, persisted_ids)
            for field_path, raw_value in _narrative_fields(row):
                text = _plain_text(raw_value)
                if not text.strip():
                    continue
                source_id = f"source_{_hash([entry_id, row_id, field_path])[:24]}"
                source_fingerprint = _hash({
                    "entry_id": entry_id,
                    "row_id": row_id,
                    "field_path": field_path,
                    "kind": kind,
                    "identity": identity,
                    "structured_facts": structured,
                    "normalized_narrative": _normalized(text),
                })
                sources.append(
                    CandidateEvidenceSource(
                        source_id=source_id,
                        entry_id=entry_id,
                        row_id=row_id,
                        kind=kind,
                        identity=identity,
                        structured_facts=structured,
                        source_field=field_path,
                        source_hash=source_fingerprint,
                        raw_value=raw_value,
                        text=text,
                    )
                )
    return sorted(sources, key=lambda item: item.source_id)


def candidate_evidence_groups(library: Sequence[Mapping[str, Any]]) -> list[tuple[str, str, dict[str, Any], dict[str, Any]]]:
    """Return source-independent structured group data, including rows without prose."""

    groups = []
    for entry in library:
        entry_id = str(entry.get("id") or "")
        kind = str(entry.get("kind") or "other")
        payload = entry.get("payload")
        rows = [row for row in payload if isinstance(row, Mapping)] if isinstance(payload, list) else []
        persisted_ids = entry.get("_row_ids") or entry.get("row_ids") or []
        for index, row in enumerate(rows):
            identity, structured = _identity_and_facts(row)
            row_id = _row_id(entry_id, row, index, persisted_ids)
            group_id = candidate_group_id(entry_id, row_id)
            groups.append((group_id, kind, identity, structured))
    return sorted(groups, key=lambda item: item[0])


def _claim_identifier(entry_id: str, row_id: str, statement: str) -> str:
    return f"claim_{_hash([entry_id, row_id, _normalized(statement)])[:24]}"


def candidate_group_id(entry_id: str, row_id: str) -> str:
    return f"source_{_hash([entry_id, row_id])[:20]}"


def _validate_and_resolve_claim(
    source: CandidateEvidenceSource,
    claim: Mapping[str, Any],
) -> CandidateEvidenceClaim:
    if set(claim) - {"statement", "support", "source_excerpt", "associated_concepts"}:
        raise CandidateEvidenceExtractionError("A proposition contains unsupported fields")
    statement = claim.get("statement")
    excerpt = claim.get("source_excerpt")
    support = claim.get("support", "explicit")
    if not isinstance(statement, str) or not statement.strip() or len(statement) > 280:
        raise CandidateEvidenceExtractionError("A proposition has an invalid statement")
    if len(statement.split()) > 18:
        raise CandidateEvidenceExtractionError("A proposition is too long to be atomic")
    if support != "explicit":
        raise CandidateEvidenceExtractionError("Narrative propositions must be explicit source evidence")
    if not isinstance(excerpt, str) or not excerpt.strip():
        raise CandidateEvidenceExtractionError("A proposition is missing its exact supporting excerpt")
    if len(excerpt) > MAX_PROPOSITION_EXCERPT_CHARACTERS:
        raise CandidateEvidenceExtractionError("A proposition source excerpt is too broad")
    start = source.text.find(excerpt)
    if start < 0:
        raise CandidateEvidenceExtractionError("A proposition excerpt does not exactly match its source")
    end = start + len(excerpt)

    raw_relations = claim.get("associated_concepts", [])
    if not isinstance(raw_relations, list):
        raise CandidateEvidenceExtractionError("Proposition concepts must be a list")
    relations: dict[tuple[str, str, str], EvidenceRelation] = {}
    for raw_relation in raw_relations:
        if not isinstance(raw_relation, Mapping):
            raise CandidateEvidenceExtractionError("A proposition relation is invalid")
        if set(raw_relation) != {"kind", "value", "relation"}:
            raise CandidateEvidenceExtractionError("A proposition relation contains unsupported fields")
        kind = raw_relation.get("kind")
        value = raw_relation.get("value")
        relation = raw_relation.get("relation")
        if kind not in _ALLOWED_CONCEPT_KINDS or relation not in _ALLOWED_RELATIONS:
            raise CandidateEvidenceExtractionError("A proposition relation uses an unsupported kind or relation")
        if not isinstance(value, str) or not value.strip() or len(value) > 160:
            raise CandidateEvidenceExtractionError("A proposition relation has an invalid concept")
        if _normalized(value) not in _normalized(excerpt):
            raise CandidateEvidenceExtractionError("A proposition concept is not present in its supporting excerpt")
        key = (str(kind), _normalized(value), str(relation))
        relations[key] = EvidenceRelation(kind=kind, value=value.strip(), relation=relation)

    provenance = EvidenceProvenance(
        library_entry_id=source.entry_id,
        library_row_id=source.row_id,
        source_field=source.source_field,
        source_hash=source.source_hash,
        source_start=start,
        source_end=end,
        source_excerpt=source.text[start:end],
        extractor_version=CANDIDATE_EVIDENCE_EXTRACTOR_VERSION,
    )
    return CandidateEvidenceClaim(
        id=_claim_identifier(source.entry_id, source.row_id, statement),
        statement=statement.strip(),
        relations=sorted(relations.values(), key=lambda item: (item.relation, item.kind, item.value.casefold())),
        provenance=provenance,
    )


def build_candidate_evidence(
    library: Sequence[Mapping[str, Any]],
    source_results: Sequence[Mapping[str, Any]],
    *,
    require_complete: bool = True,
    source_ids: set[str] | None = None,
) -> CandidateEvidenceExtraction:
    """Validate isolated extraction results and construct provenance-backed evidence."""

    all_sources = iter_candidate_sources(library)
    if source_ids is None:
        sources = all_sources
    else:
        all_source_ids = {source.source_id for source in all_sources}
        if not source_ids <= all_source_ids:
            raise CandidateEvidenceExtractionError("A selected source ID is not in the current Library")
        sources = [source for source in all_sources if source.source_id in source_ids]
    source_by_id = {source.source_id: source for source in sources}
    results_by_id: dict[str, Mapping[str, Any]] = {}
    for result in source_results:
        if not isinstance(result, Mapping):
            raise CandidateEvidenceExtractionError("An isolated proposition result is invalid")
        source_id = result.get("source_id")
        if not isinstance(source_id, str) or source_id not in source_by_id or source_id in results_by_id:
            raise CandidateEvidenceExtractionError("An isolated result has an unknown or duplicate source ID")
        results_by_id[source_id] = result
    if require_complete and set(results_by_id) != set(source_by_id):
        raise CandidateEvidenceExtractionError("Isolated results do not cover each narrative source exactly once")

    claims_by_group: dict[str, dict[str, CandidateEvidenceClaim]] = {}
    source_to_group = {
        source.source_id: candidate_group_id(source.entry_id, source.row_id)
        for source in sources
    }
    for source_id in sorted(results_by_id):
        source = source_by_id[source_id]
        raw_claims = results_by_id[source_id].get("claims")
        if not isinstance(raw_claims, list) or len(raw_claims) > 80:
            raise CandidateEvidenceExtractionError("A source result must contain a bounded claims list")
        group_claims = claims_by_group.setdefault(source_to_group[source_id], {})
        for raw_claim in raw_claims:
            if not isinstance(raw_claim, Mapping):
                raise CandidateEvidenceExtractionError("A proposition result is invalid")
            claim = _validate_and_resolve_claim(source, raw_claim)
            existing = group_claims.get(claim.id)
            if existing is None:
                group_claims[claim.id] = claim
            else:
                merged_relations = {
                    (item.kind, _normalized(item.value), item.relation): item
                    for item in [*existing.relations, *claim.relations]
                }
                group_claims[claim.id] = existing.model_copy(
                    update={"relations": sorted(merged_relations.values(), key=lambda item: (item.relation, item.kind, item.value.casefold()))}
                )

    groups: list[CandidateEvidenceGroup] = []
    all_groups = candidate_evidence_groups(library)
    selected_group_ids = (
        {group_id for group_id, _kind, _identity, _facts in all_groups}
        if source_ids is None
        else set(source_to_group.values())
    )
    for group_id, kind, identity, structured in all_groups:
        if group_id not in selected_group_ids:
            continue
        claims = sorted(claims_by_group.get(group_id, {}).values(), key=lambda item: item.id)
        groups.append(CandidateEvidenceGroup(id=group_id, kind=kind, identity=identity, structured_facts=structured, claims=claims))

    extraction = CandidateEvidenceExtraction(
        groups=groups,
    )
    validate_provenance(
        extraction,
        {(source.entry_id, source.row_id, source.source_field): source.text for source in sources},
    )
    return extraction


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


def validate_provenance(
    extraction: CandidateEvidenceExtraction,
    sources: Mapping[tuple[str, str, str], str],
) -> None:
    """Raise when an internal claim cannot be resolved to its exact source span."""

    for group in extraction.groups:
        for claim in group.claims:
            provenance = claim.provenance
            source = sources.get((provenance.library_entry_id, provenance.library_row_id, provenance.source_field))
            if source is None:
                raise CandidateEvidenceExtractionError(f"orphan candidate evidence claim: {claim.id}")
            if source[provenance.source_start:provenance.source_end] != provenance.source_excerpt:
                raise CandidateEvidenceExtractionError(f"candidate evidence source span mismatch: {claim.id}")


__all__ = [
    "CANDIDATE_EVIDENCE_EXTRACTOR_VERSION",
    "CANDIDATE_EVIDENCE_PROMPT_VERSION",
    "CANDIDATE_EVIDENCE_PROPOSITION_MODEL",
    "CANDIDATE_EVIDENCE_PROPOSITION_MODEL_REVISION",
    "CANDIDATE_EVIDENCE_SCHEMA_VERSION",
    "MAX_PROPOSITION_EXCERPT_CHARACTERS",
    "CandidateEvidenceExtractionError",
    "CandidateEvidenceExtraction",
    "CandidateEvidenceProjection",
    "CandidateEvidenceSource",
    "build_candidate_evidence",
    "candidate_group_id",
    "candidate_evidence_groups",
    "composer_projection",
    "iter_candidate_sources",
    "validate_provenance",
]
