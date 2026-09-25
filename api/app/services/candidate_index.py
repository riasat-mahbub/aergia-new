"""Persistent deterministic candidate index and per-source semantic cache."""

from __future__ import annotations

import copy
import re
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_index import (
    CandidateIndexSource,
    CandidateIndexState,
    CandidateIndexTerm,
    CandidateSemanticRecord,
)
from app.models.library import Library, LibraryEntry
from app.services.candidate_evidence import (
    CANDIDATE_EVIDENCE_EXTRACTOR_VERSION,
    CANDIDATE_EVIDENCE_PROMPT_VERSION,
    CANDIDATE_EVIDENCE_PROPOSITION_MODEL,
    CANDIDATE_EVIDENCE_PROPOSITION_MODEL_REVISION,
    CANDIDATE_EVIDENCE_SCHEMA_VERSION,
    CandidateEvidenceExtractionError,
    CandidateEvidenceSource,
    _identity_and_facts,
    _narrative_fields,
    _normalized,
    _plain_text,
    _validate_and_resolve_claim,
    _hash,
    iter_candidate_sources,
)
from app.scanner.skills import extract_skills


SemanticState = Literal["FRESH", "STALE", "MISSING"]
MAX_REFRESH_SOURCES = 24
MAX_REFRESH_CHARACTERS = 48_000
MAX_WRITER_CONTEXT_CHARACTERS = 42_000
MAX_WRITER_SOURCE_CHARACTERS = 8_000
CANDIDATE_DETERMINISTIC_INDEX_VERSION = "candidate-deterministic-v1"
_SEARCH_STOP_WORDS = frozenset({
    "about", "after", "also", "and", "are", "build", "for", "from", "have",
    "into", "more", "must", "other", "software", "such", "that", "their",
    "them", "this", "through", "using", "with", "work", "working", "years",
})


def assign_stable_row_ids(
    payload: Sequence[Any],
    previous_ids: Sequence[Any] = (),
    previous_payload: Sequence[Any] = (),
) -> list[str]:
    """Preserve identity across content edits, insertions, deletions, and reordering."""

    old_by_content: dict[str, list[str]] = {}
    for index, value in enumerate(previous_payload):
        if index < len(previous_ids) and isinstance(previous_ids[index], str):
            old_by_content.setdefault(_hash(value), []).append(previous_ids[index])

    row_ids: list[str | None] = [None] * len(payload)
    used: set[str] = set()
    unmatched: list[int] = []
    for index, value in enumerate(payload):
        explicit_id = value.get("id") if isinstance(value, Mapping) else None
        stable_id = explicit_id.strip() if isinstance(explicit_id, str) and explicit_id.strip() else None
        if stable_id is None:
            matches = old_by_content.get(_hash(value), [])
            while matches and matches[0] in used:
                matches.pop(0)
            if matches:
                stable_id = matches.pop(0)
        if stable_id is not None and stable_id not in used:
            row_ids[index] = stable_id[:128]
            used.add(stable_id)
        else:
            unmatched.append(index)

    # Same-position edits preserve the prior immutable ID after unchanged rows
    # have been matched across moves.
    for index in unmatched:
        previous_id = previous_ids[index] if index < len(previous_ids) else None
        if isinstance(previous_id, str) and previous_id.strip() and previous_id not in used:
            row_ids[index] = previous_id[:128]
            used.add(previous_id)

    for index in unmatched:
        if row_ids[index] is None:
            row_id = str(uuid.uuid4())
            while row_id in used:
                row_id = str(uuid.uuid4())
            row_ids[index] = row_id
            used.add(row_id)
    return [row_id for row_id in row_ids if row_id is not None]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _search_terms(text: str, canonical_skills: Sequence[str] = ()) -> set[str]:
    terms = {str(skill).casefold()[:160] for skill in canonical_skills if str(skill).strip()}
    for token in re.findall(r"(?<![\w])[\w][\w.+#-]{0,158}(?![\w])", text.casefold()):
        token = token.strip(".+#-")
        if len(token) < 2 or token in _SEARCH_STOP_WORDS:
            continue
        terms.add(token[:160])
        for part in re.split(r"[.+#_-]+", token):
            if len(part) >= 3 and part not in _SEARCH_STOP_WORDS:
                terms.add(part[:160])
        if token.startswith(("collaborat", "communicat", "document", "consult", "test")):
            terms.add(next(prefix for prefix in ("collaborat", "communicat", "document", "consult", "test") if token.startswith(prefix)))
        elif token.endswith("s") and not token.endswith("ss") and len(token) > 4:
            terms.add(token[:-1])
    return terms


def _source_id(entry_id: str, row_id: str, field_path: str) -> str:
    return f"source_{_hash([entry_id, row_id, field_path])[:24]}"


def _row_index_record(
    entry: LibraryEntry,
    row_id: str,
    row: Mapping[str, Any],
) -> dict[str, Any]:
    identity, facts = _identity_and_facts(row)
    text = " ".join(
        part for part in (
            " ".join(str(value) for value in identity.values() if value is not None),
            " ".join(str(value) for value in facts.values() if value is not None),
            " ".join(_plain_text(raw) for _, raw in _narrative_fields(row)),
        ) if part
    )
    normalized = _normalized(text)
    metadata = {
        "entry_id": entry.id,
        "row_id": row_id,
        "field_path": "$row",
        "kind": entry.kind,
        "identity": identity,
        "structured_facts": facts,
        "normalized_narrative": normalized,
    }
    return {
        "source_id": _source_id(entry.id, row_id, "$row"),
        "entry_id": entry.id,
        "row_id": row_id,
        "field_path": "$row",
        "kind": entry.kind,
        "source_fingerprint": _hash(metadata),
        "identity": identity,
        "structured_facts": facts,
        "canonical_skills": sorted(extract_skills(text)),
        "normalized_text": normalized,
        "narrative": "",
    }


def _narrative_index_records(entry: LibraryEntry) -> list[dict[str, Any]]:
    indexed_entry = {
        "id": entry.id,
        "kind": entry.kind,
        "payload": copy.deepcopy(entry.payload or []),
        "_row_ids": list(entry.row_ids or []),
    }
    result: list[dict[str, Any]] = []
    for source in iter_candidate_sources([indexed_entry]):
        result.append({
            "source_id": source.source_id,
            "entry_id": source.entry_id,
            "row_id": source.row_id,
            "field_path": source.source_field,
            "kind": source.kind,
            "source_fingerprint": source.source_hash,
            "identity": source.identity,
            "structured_facts": source.structured_facts,
            "canonical_skills": sorted(extract_skills(" ".join((
                *[str(value) for value in source.identity.values() if value is not None],
                *[str(value) for value in source.structured_facts.values() if value is not None],
                source.text,
            )))),
            "normalized_text": _normalized(" ".join((str(v) for v in [*source.identity.values(), *source.structured_facts.values(), source.text] if v is not None))),
            "narrative": source.text,
        })
    return result


def _as_evidence_source(source: CandidateIndexSource) -> CandidateEvidenceSource:
    return CandidateEvidenceSource(
        source_id=source.source_id,
        entry_id=source.library_entry_id,
        row_id=source.row_id,
        kind=source.kind,
        identity=source.identity or {},
        structured_facts=source.structured_facts or {},
        source_field=source.field_path,
        source_hash=source.source_fingerprint,
        raw_value=source.narrative,
        text=source.narrative,
        canonical_skills=list(source.canonical_skills or []),
    )


class CandidateIndexService:
    """Own source identity, deterministic projection, cache freshness and writes."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _semantic_state(source: CandidateIndexSource, record: CandidateSemanticRecord | None) -> SemanticState:
        if record is None:
            return "MISSING"
        fresh = (
            record.source_fingerprint == source.source_fingerprint
            and record.proposition_model == CANDIDATE_EVIDENCE_PROPOSITION_MODEL
            and record.proposition_model_revision == CANDIDATE_EVIDENCE_PROPOSITION_MODEL_REVISION
            and record.extractor_version == CANDIDATE_EVIDENCE_EXTRACTOR_VERSION
            and record.prompt_version == CANDIDATE_EVIDENCE_PROMPT_VERSION
            and record.schema_version == CANDIDATE_EVIDENCE_SCHEMA_VERSION
        )
        if not fresh:
            return "STALE"
        result = record.semantic_result if isinstance(record.semantic_result, Mapping) else {}
        claims = result.get("claims")
        if not isinstance(claims, list) or len(claims) > 80:
            return "STALE"
        evidence_source = _as_evidence_source(source)
        try:
            if any(not isinstance(claim, Mapping) for claim in claims):
                return "STALE"
            for claim in claims:
                _validate_and_resolve_claim(evidence_source, claim)
        except (CandidateEvidenceExtractionError, TypeError, ValueError):
            return "STALE"
        return "FRESH"

    async def _desired_for_entry(self, entry: LibraryEntry) -> dict[str, dict[str, Any]]:
        payload = entry.payload if isinstance(entry.payload, list) else []
        stable_ids = assign_stable_row_ids(payload, entry.row_ids or [])
        if stable_ids != (entry.row_ids or []):
            entry.row_ids = stable_ids
        desired: dict[str, dict[str, Any]] = {}
        narratives = {row["source_id"]: row for row in _narrative_index_records(entry)}
        for index, row in enumerate(payload):
            if not isinstance(row, Mapping):
                continue
            row_record = _row_index_record(entry, stable_ids[index], row)
            row_record["library_entry_id"] = row_record.pop("entry_id")
            desired[row_record["source_id"]] = row_record
        for record in narratives.values():
            record["library_entry_id"] = record.pop("entry_id")
        desired.update(narratives)
        return desired

    async def _load_sources(self, user_id: str) -> list[CandidateIndexSource]:
        result = await self.db.execute(
            select(CandidateIndexSource).where(CandidateIndexSource.user_id == user_id)
        )
        return list(result.scalars().all())

    async def _upsert_desired(
        self,
        user_id: str,
        entry_ids: set[str],
        desired: Mapping[str, Mapping[str, Any]],
    ) -> None:
        if not entry_ids:
            return
        current_result = await self.db.execute(
            select(CandidateIndexSource).where(
                CandidateIndexSource.user_id == user_id,
                CandidateIndexSource.library_entry_id.in_(entry_ids),
            )
        )
        current = {row.source_id: row for row in current_result.scalars().all()}
        terms_to_replace: dict[str, set[str]] = {}
        for source_id in current.keys() - desired.keys():
            await self.db.execute(
                delete(CandidateSemanticRecord).where(CandidateSemanticRecord.source_id == source_id)
            )
            await self.db.execute(
                delete(CandidateIndexTerm).where(CandidateIndexTerm.source_id == source_id)
            )
            await self.db.delete(current[source_id])
        for source_id, values in desired.items():
            row = current.get(source_id)
            if row is None:
                self.db.add(CandidateIndexSource(user_id=user_id, **values, updated_at=_now()))
                terms_to_replace[source_id] = _search_terms(values["normalized_text"], values["canonical_skills"])
                continue
            if any(getattr(row, name) != value for name, value in values.items()):
                for name, value in values.items():
                    setattr(row, name, value)
                row.updated_at = _now()
                terms_to_replace[source_id] = _search_terms(values["normalized_text"], values["canonical_skills"])
        await self.db.flush()
        for source_id, terms in terms_to_replace.items():
            await self.db.execute(
                delete(CandidateIndexTerm).where(CandidateIndexTerm.source_id == source_id)
            )
            for term in terms:
                self.db.add(CandidateIndexTerm(source_id=source_id, user_id=user_id, term=term))
        await self.db.flush()

    async def ensure_current(self, user_id: str) -> list[CandidateIndexSource]:
        state = await self.db.get(CandidateIndexState, user_id)
        if state is not None and state.deterministic_version == CANDIDATE_DETERMINISTIC_INDEX_VERSION:
            return await self._load_sources(user_id)

        library_result = await self.db.execute(select(Library).where(Library.user_id == user_id))
        library = library_result.scalar_one_or_none()
        if library is None:
            if state is None:
                self.db.add(CandidateIndexState(
                    user_id=user_id,
                    deterministic_version=CANDIDATE_DETERMINISTIC_INDEX_VERSION,
                    backfilled_at=_now(),
                ))
            else:
                state.deterministic_version = CANDIDATE_DETERMINISTIC_INDEX_VERSION
                state.backfilled_at = _now()
            await self.db.flush()
            return []
        entries_result = await self.db.execute(
            select(LibraryEntry).where(LibraryEntry.library_id == library.id).order_by(LibraryEntry.created_at.asc())
        )
        entries = list(entries_result.scalars().all())
        desired_by_entry: dict[str, dict[str, dict[str, Any]]] = {}
        for entry in entries:
            desired_by_entry[entry.id] = await self._desired_for_entry(entry)
        for entry_id, desired in desired_by_entry.items():
            await self._upsert_desired(user_id, {entry_id}, desired)
        all_desired_ids = {source_id for desired in desired_by_entry.values() for source_id in desired}
        indexed_sources = await self.db.execute(
            select(CandidateIndexSource).where(CandidateIndexSource.user_id == user_id)
        )
        for source in indexed_sources.scalars().all():
            if source.source_id not in all_desired_ids:
                await self.db.execute(
                    delete(CandidateSemanticRecord).where(CandidateSemanticRecord.source_id == source.source_id)
                )
                await self.db.execute(
                    delete(CandidateIndexTerm).where(CandidateIndexTerm.source_id == source.source_id)
                )
                await self.db.delete(source)
        if state is None:
            self.db.add(CandidateIndexState(
                user_id=user_id,
                deterministic_version=CANDIDATE_DETERMINISTIC_INDEX_VERSION,
                backfilled_at=_now(),
            ))
        else:
            state.deterministic_version = CANDIDATE_DETERMINISTIC_INDEX_VERSION
            state.backfilled_at = _now()
        await self.db.flush()
        return await self._load_sources(user_id)

    async def library_entry_changed(self, entry: LibraryEntry, user_id: str) -> None:
        await self.ensure_current(user_id)
        await self._upsert_desired(user_id, {entry.id}, await self._desired_for_entry(entry))
        await self.db.flush()

    async def library_entry_deleted(self, entry_id: str, user_id: str) -> None:
        await self.ensure_current(user_id)
        await self._upsert_desired(user_id, {entry_id}, {})
        await self.db.flush()

    async def search_sources(
        self,
        user_id: str,
        query_text: str,
        *,
        max_sources: int = 500,
    ) -> list[CandidateIndexSource]:
        """Retrieve high-recall deterministic sources through the token index."""

        terms = sorted(_search_terms(query_text, extract_skills(query_text)))[:800]
        if not terms:
            return []
        matching = await self.db.execute(
            select(CandidateIndexTerm.source_id, func.count().label("match_count"))
            .where(CandidateIndexTerm.user_id == user_id, CandidateIndexTerm.term.in_(terms))
            .group_by(CandidateIndexTerm.source_id)
            .order_by(func.count().desc(), CandidateIndexTerm.source_id.asc())
            .limit(max(1, min(max_sources, 1_000)))
        )
        source_ids = [row.source_id for row in matching.all()]
        if not source_ids:
            return []
        result = await self.db.execute(
            select(CandidateIndexSource).where(
                CandidateIndexSource.user_id == user_id,
                CandidateIndexSource.source_id.in_(source_ids),
            )
        )
        sources_by_id = {source.source_id: source for source in result.scalars().all()}
        return [sources_by_id[source_id] for source_id in source_ids if source_id in sources_by_id]

    async def states(self, user_id: str) -> tuple[list[CandidateIndexSource], dict[str, int], dict[str, CandidateSemanticRecord]]:
        sources = await self.ensure_current(user_id)
        record_result = await self.db.execute(
            select(CandidateSemanticRecord)
            .join(CandidateIndexSource, CandidateSemanticRecord.source_id == CandidateIndexSource.source_id)
            .where(CandidateIndexSource.user_id == user_id)
        )
        records = {record.source_id: record for record in record_result.scalars().all()}
        counts = {"FRESH": 0, "STALE": 0, "MISSING": 0}
        for source in sources:
            if source.field_path == "$row":
                continue
            counts[self._semantic_state(source, records.get(source.source_id))] += 1
        return sources, counts, records

    async def refresh_batch_sources(
        self,
        user_id: str,
        *,
        max_sources: int = MAX_REFRESH_SOURCES,
        max_characters: int = MAX_REFRESH_CHARACTERS,
    ) -> tuple[list[CandidateIndexSource], dict[str, int]]:
        sources, counts, records = await self.states(user_id)
        stale: list[CandidateIndexSource] = []
        used = 0
        for source in sorted(sources, key=lambda item: (item.kind, item.source_id)):
            if source.field_path == "$row" or self._semantic_state(source, records.get(source.source_id)) == "FRESH":
                continue
            cost = len(source.narrative) + 800
            if cost > max_characters:
                continue
            if stale and (len(stale) >= max_sources or used + cost > max_characters):
                continue
            stale.append(source)
            used += cost
            if len(stale) >= max_sources or used >= max_characters:
                break
        return stale, counts

    async def persist_refresh_results(
        self,
        user_id: str,
        results: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        sources, _, _ = await self.states(user_id)
        source_by_id = {source.source_id: source for source in sources if source.field_path != "$row"}
        occurrences: dict[str, int] = {}
        for raw in results:
            source_id = raw.get("source_id") if isinstance(raw, Mapping) else None
            if isinstance(source_id, str):
                occurrences[source_id] = occurrences.get(source_id, 0) + 1
        accepted: list[str] = []
        rejected: list[str] = []
        for raw in results:
            if not isinstance(raw, Mapping):
                continue
            source_id = raw.get("source_id")
            source = source_by_id.get(source_id) if isinstance(source_id, str) else None
            if (
                source is None
                or occurrences.get(source_id, 0) != 1
                or set(raw) - {"source_id", "source_fingerprint", "claims"}
            ):
                if isinstance(source_id, str):
                    rejected.append(source_id)
                continue
            if raw.get("source_fingerprint") != source.source_fingerprint:
                rejected.append(source_id)
                continue
            claims = raw.get("claims")
            if not isinstance(claims, list) or len(claims) > 80:
                rejected.append(source_id)
                continue
            evidence_source = _as_evidence_source(source)
            try:
                validated = [_validate_and_resolve_claim(evidence_source, claim) for claim in claims if isinstance(claim, Mapping)]
                if len(validated) != len(claims):
                    raise CandidateEvidenceExtractionError("Malformed claim")
            except (CandidateEvidenceExtractionError, TypeError, ValueError):
                rejected.append(source_id)
                continue
            semantic_result = {
                "claims": [copy.deepcopy(dict(claim)) for claim in claims],
            }
            # Lock and re-read the authoritative Library row immediately
            # before writing. A result extracted from F1 cannot become fresh
            # after a concurrent edit has made the Library source F2.
            entry_result = await self.db.execute(
                select(LibraryEntry)
                .join(Library, LibraryEntry.library_id == Library.id)
                .where(LibraryEntry.id == source.library_entry_id, Library.user_id == user_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            entry = entry_result.scalar_one_or_none()
            if entry is None:
                rejected.append(source_id)
                continue
            current_sources = iter_candidate_sources([{
                "id": entry.id,
                "kind": entry.kind,
                "payload": entry.payload or [],
                "_row_ids": entry.row_ids or [],
            }])
            authoritative = next((item for item in current_sources if item.source_id == source_id), None)
            current_result = await self.db.execute(
                select(CandidateIndexSource)
                .where(CandidateIndexSource.source_id == source_id, CandidateIndexSource.user_id == user_id)
                .execution_options(populate_existing=True)
            )
            current = current_result.scalar_one_or_none()
            if (
                authoritative is None
                or authoritative.source_hash != raw.get("source_fingerprint")
                or current is None
                or current.source_fingerprint != raw.get("source_fingerprint")
            ):
                rejected.append(source_id)
                continue
            semantic_result_row = await self.db.get(CandidateSemanticRecord, source_id)
            values = {
                "source_id": source_id,
                "source_fingerprint": current.source_fingerprint,
                "proposition_model": CANDIDATE_EVIDENCE_PROPOSITION_MODEL,
                "proposition_model_revision": CANDIDATE_EVIDENCE_PROPOSITION_MODEL_REVISION,
                "extractor_version": CANDIDATE_EVIDENCE_EXTRACTOR_VERSION,
                "prompt_version": CANDIDATE_EVIDENCE_PROMPT_VERSION,
                "schema_version": CANDIDATE_EVIDENCE_SCHEMA_VERSION,
                "semantic_result": semantic_result,
                "refreshed_at": _now(),
            }
            if semantic_result_row is None:
                self.db.add(CandidateSemanticRecord(**values))
            else:
                for name, value in values.items():
                    setattr(semantic_result_row, name, value)
            accepted.append(source_id)
        await self.db.flush()
        _, counts, _ = await self.states(user_id)
        return {"accepted_source_ids": accepted, "rejected_source_ids": rejected, "source_counts": counts}

    async def fresh_semantic_results(
        self,
        user_id: str,
    ) -> tuple[list[CandidateIndexSource], list[dict[str, Any]], dict[str, int]]:
        sources, counts, records = await self.states(user_id)
        usable = [
            source for source in sources
            if source.field_path != "$row" and self._semantic_state(source, records.get(source.source_id)) == "FRESH"
        ]
        results = [
            {
                "source_id": source.source_id,
                "source_fingerprint": source.source_fingerprint,
                "claims": (records[source.source_id].semantic_result or {}).get("claims", []),
            }
            for source in usable
        ]
        return usable, results, counts

    async def deterministic_summary(self, user_id: str) -> dict[str, Any]:
        sources, counts, _ = await self.states(user_id)
        row_sources = [source for source in sources if source.field_path == "$row"]
        skills = sorted({skill for source in sources for skill in (source.canonical_skills or [])})
        return {
            "schema_version": "candidate-index-v1",
            "canonical_skills": skills,
            "source_count": len([source for source in sources if source.field_path != "$row"]),
            "row_count": len(row_sources),
            "semantic_source_counts": {key.lower(): value for key, value in counts.items()},
        }


__all__ = [
    "CANDIDATE_DETERMINISTIC_INDEX_VERSION",
    "CandidateIndexService",
    "MAX_REFRESH_CHARACTERS",
    "MAX_REFRESH_SOURCES",
    "MAX_WRITER_CONTEXT_CHARACTERS",
    "MAX_WRITER_SOURCE_CHARACTERS",
    "assign_stable_row_ids",
]
