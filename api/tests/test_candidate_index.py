"""Persistent candidate-index freshness, identity, and partial-write contracts."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.session import async_session
from app.http_schemas.library import LibraryEntryCreate, LibraryEntryUpdate
from app.models.candidate_index import CandidateIndexSource, CandidateIndexState, CandidateSemanticRecord
from app.services.candidate_index import CandidateIndexService
from app.services.library import LibraryService


async def _create_entry(user_id: str, payload: list[dict]) -> str:
    async with async_session() as db:
        entry = await LibraryService(db).create_entry(
            user_id,
            LibraryEntryCreate(kind="experience", payload=payload),
        )
        entry_id = entry.id
        await db.commit()
        return entry_id


async def _sources(user_id: str, entry_id: str) -> list[CandidateIndexSource]:
    async with async_session() as db:
        result = await db.execute(
            select(CandidateIndexSource)
            .where(CandidateIndexSource.user_id == user_id, CandidateIndexSource.library_entry_id == entry_id)
            .order_by(CandidateIndexSource.source_id)
        )
        return list(result.scalars().all())


@pytest.mark.asyncio
async def test_legacy_row_identity_is_lazily_persisted_then_survives_edit(user_id, clean_library):
    entry_id = await _create_entry(user_id, [{
        "company": "Example",
        "description": "Built Python services.",
    }])
    async with async_session() as db:
        entry = await LibraryService(db).get_entry(entry_id, user_id)
        assert entry is not None
        entry.row_ids = []
        index_state = await db.get(CandidateIndexState, user_id)
        assert index_state is not None
        index_state.deterministic_version = "legacy"
        indexed = await CandidateIndexService(db).ensure_current(user_id)
        persisted_row_id = next(source.row_id for source in indexed if source.field_path == "$row")
        await db.commit()

    async with async_session() as db:
        entry = await LibraryService(db).get_entry(entry_id, user_id)
        assert entry is not None
        assert entry.row_ids == [persisted_row_id]
        await LibraryService(db).update_entry(entry_id, user_id, LibraryEntryUpdate(payload=[{
            "company": "Example",
            "description": "Built Python and PostgreSQL services.",
        }]))
        await db.commit()

    after = await _sources(user_id, entry_id)
    narrative = next(source for source in after if source.field_path == "description")
    assert narrative.row_id == persisted_row_id


@pytest.mark.asyncio
async def test_row_identity_survives_edit_and_fingerprint_changes(user_id, clean_library):
    entry_id = await _create_entry(user_id, [{
        "company": "Example",
        "position": "Engineer",
        "description": "Built Python services.",
    }])
    before = await _sources(user_id, entry_id)
    narrative_before = next(source for source in before if source.field_path == "description")
    async with async_session() as db:
        await CandidateIndexService(db).persist_refresh_results(user_id, [{
            "source_id": narrative_before.source_id,
            "source_fingerprint": narrative_before.source_fingerprint,
            "claims": [],
        }])
        await db.commit()

    async with async_session() as db:
        entry = await LibraryService(db).get_entry(entry_id, user_id)
        assert entry is not None
        await LibraryService(db).update_entry(entry_id, user_id, LibraryEntryUpdate(payload=[{
            "company": "Example",
            "position": "Engineer",
            "description": "Built Python and PostgreSQL services.",
        }]))
        await db.commit()

    after = await _sources(user_id, entry_id)
    narrative_after = next(source for source in after if source.field_path == "description")
    assert narrative_after.source_id == narrative_before.source_id
    assert narrative_after.row_id == narrative_before.row_id
    assert narrative_after.source_fingerprint != narrative_before.source_fingerprint

    async with async_session() as db:
        _indexed_sources, counts, _records = await CandidateIndexService(db).states(user_id)
    assert counts == {"FRESH": 0, "STALE": 1, "MISSING": 0}


@pytest.mark.asyncio
async def test_partial_refresh_persists_good_sources_and_retries_only_failed_source(user_id, clean_library):
    entry_id = await _create_entry(user_id, [
        {"id": "row-a", "company": "A", "description": "Built Python services."},
        {"id": "row-b", "company": "B", "description": "Tested PostgreSQL migrations."},
    ])
    sources = [source for source in await _sources(user_id, entry_id) if source.field_path != "$row"]
    source_a, source_b = sources

    async with async_session() as db:
        service = CandidateIndexService(db)
        result = await service.persist_refresh_results(user_id, [
            {"source_id": source_a.source_id, "source_fingerprint": source_a.source_fingerprint, "claims": []},
            {"source_id": source_b.source_id, "source_fingerprint": source_b.source_fingerprint, "claims": "malformed"},
        ])
        await db.commit()
    assert result["accepted_source_ids"] == [source_a.source_id]
    assert result["rejected_source_ids"] == [source_b.source_id]
    assert result["source_counts"] == {"FRESH": 1, "STALE": 0, "MISSING": 1}

    async with async_session() as db:
        retry_sources, counts = await CandidateIndexService(db).refresh_batch_sources(user_id)
    assert counts == {"FRESH": 1, "STALE": 0, "MISSING": 1}
    assert [source.source_id for source in retry_sources] == [source_b.source_id]

    async with async_session() as db:
        refreshed = await CandidateIndexService(db).persist_refresh_results(user_id, [{
            "source_id": source_b.source_id,
            "source_fingerprint": source_b.source_fingerprint,
            "claims": [],
        }])
        await db.commit()
    assert refreshed["accepted_source_ids"] == [source_b.source_id]
    async with async_session() as db:
        warm_sources, counts = await CandidateIndexService(db).refresh_batch_sources(user_id)
    assert warm_sources == []
    assert counts == {"FRESH": 2, "STALE": 0, "MISSING": 0}


@pytest.mark.asyncio
async def test_refresh_result_is_discarded_when_library_source_changes(user_id, clean_library):
    entry_id = await _create_entry(user_id, [{
        "company": "Example",
        "description": "Built Python services.",
    }])
    source = next(source for source in await _sources(user_id, entry_id) if source.field_path == "description")
    async with async_session() as db:
        initial = await CandidateIndexService(db).persist_refresh_results(user_id, [{
            "source_id": source.source_id,
            "source_fingerprint": source.source_fingerprint,
            "claims": [],
        }])
        await db.commit()
    assert initial["accepted_source_ids"] == [source.source_id]

    async with async_session() as db:
        entry = await LibraryService(db).get_entry(entry_id, user_id)
        assert entry is not None
        await LibraryService(db).update_entry(entry_id, user_id, LibraryEntryUpdate(payload=[{
            "company": "Example",
            "description": "Built Python and Redis services.",
        }]))
        await db.commit()

    refresh_source = next(source for source in await _sources(user_id, entry_id) if source.field_path == "description")
    async with async_session() as db:
        stale_sources, counts = await CandidateIndexService(db).refresh_batch_sources(user_id)
    assert counts == {"FRESH": 0, "STALE": 1, "MISSING": 0}
    assert stale_sources[0].source_fingerprint == refresh_source.source_fingerprint

    async with async_session() as db:
        await LibraryService(db).update_entry(entry_id, user_id, LibraryEntryUpdate(payload=[{
            "company": "Example",
            "description": "Built Python, Redis, and Docker services.",
        }]))
        await db.commit()

    async with async_session() as db:
        result = await CandidateIndexService(db).persist_refresh_results(user_id, [{
            "source_id": source.source_id,
            "source_fingerprint": refresh_source.source_fingerprint,
            "claims": [],
        }])
        await db.commit()
    assert result["accepted_source_ids"] == []
    assert result["rejected_source_ids"] == [source.source_id]
    assert result["source_counts"] == {"FRESH": 0, "STALE": 1, "MISSING": 0}


@pytest.mark.asyncio
async def test_library_deletion_removes_deterministic_and_semantic_sources(user_id, clean_library):
    entry_id = await _create_entry(user_id, [{
        "company": "Example",
        "description": "Built Python services.",
    }])
    source = next(source for source in await _sources(user_id, entry_id) if source.field_path == "description")
    async with async_session() as db:
        await CandidateIndexService(db).persist_refresh_results(user_id, [{
            "source_id": source.source_id,
            "source_fingerprint": source.source_fingerprint,
            "claims": [],
        }])
        await db.commit()

    async with async_session() as db:
        assert await LibraryService(db).delete_entry(entry_id, user_id)
        await db.commit()
        assert await db.get(CandidateIndexSource, source.source_id) is None
        assert await db.get(CandidateSemanticRecord, source.source_id) is None


@pytest.mark.asyncio
async def test_indexed_query_matches_unknown_technology_as_a_whole_token(user_id, clean_library):
    entry_id = await _create_entry(user_id, [{
        "company": "Example",
        "tech_stack": ["Postgres"],
        "description": "Integrated Fabrikam-SDK into internal APIs.",
    }])
    async with async_session() as db:
        index = CandidateIndexService(db)
        unknown_match = await index.search_sources(user_id, "Fabrikam-SDK")
        partial_match = await index.search_sources(user_id, "Fabrika")
        alias_match = await index.search_sources(user_id, "PostgreSQL")

    assert unknown_match
    assert all(source.library_entry_id == entry_id for source in unknown_match)
    assert partial_match == []
    assert alias_match
    assert any("postgresql" in source.canonical_skills for source in alias_match)
