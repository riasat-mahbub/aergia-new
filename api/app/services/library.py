"""Library service layer.

Owns the per-user Library + LibraryEntry lifecycle: get-or-create the
singleton Library row, CRUD on entries, clone an entry into a
``SectionInstance`` for the CV builder, and promote a CV's eligible
sections into new Library entries.

Concurrency: ``_get_or_create_library`` is race-safe via an
``IntegrityError`` catch — two concurrent first writes cannot both
insert because ``user_id`` is ``UNIQUE``. The loser re-SELECTs and
returns the winner.

Vocabulary: Library kinds and CV section types share the same
singular names (``experience``, ``education``, ``skill``, ``project``,
``certification``, ``language``). No translation is needed between
the two. ``profile`` and ``summary`` stay authored inside the CV
because their ``data`` shape is a dict, not a list of entries.
"""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cv import CV
from app.models.library import Library, LibraryEntry
from app.schema.models import SectionInstance
from app.schemas.library import LIBRARY_ENTRY_KINDS, LibraryEntryCreate, LibraryEntryUpdate


@dataclass
class PromoteResult:
    """Internal return type for ``promote_cv_to_library``."""

    library_id: str
    promoted: dict[str, int]
    skipped: list[str]


def _content_hash(payload: list[dict]) -> str:
    """Stable sha256 of a payload for content-based dedupe."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def _derive_title(payload: list[dict], kind: str) -> str:
    """Best-effort title from the first payload entry; falls back to the kind."""
    if payload:
        first = payload[0]
        if isinstance(first, dict):
            t = first.get("title") or first.get("text") or first.get("name")
            if isinstance(t, str) and t.strip():
                return t.strip()[:120]
    return kind.capitalize()


class LibraryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_or_create_library(self, user_id: str) -> Library:
        result = await self.db.execute(select(Library).where(Library.user_id == user_id))
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing
        new_lib = Library(user_id=user_id)
        self.db.add(new_lib)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            result = await self.db.execute(
                select(Library).where(Library.user_id == user_id)
            )
            return result.scalar_one()
        return new_lib

    async def list_entries(
        self, user_id: str, kind: str | None = None
    ) -> list[LibraryEntry]:
        library = await self._get_or_create_library(user_id)
        stmt = select(LibraryEntry).where(LibraryEntry.library_id == library.id)
        if kind is not None:
            stmt = stmt.where(LibraryEntry.kind == kind)
        stmt = stmt.order_by(LibraryEntry.created_at.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_entry(
        self, user_id: str, data: LibraryEntryCreate
    ) -> LibraryEntry:
        library = await self._get_or_create_library(user_id)
        entry = LibraryEntry(library_id=library.id, kind=data.kind.value, payload=data.payload)
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_entry(self, entry_id: str, user_id: str) -> LibraryEntry | None:
        stmt = (
            select(LibraryEntry)
            .join(Library, LibraryEntry.library_id == Library.id)
            .where(LibraryEntry.id == entry_id, Library.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_entry(
        self, entry_id: str, user_id: str, data: LibraryEntryUpdate
    ) -> LibraryEntry | None:
        entry = await self.get_entry(entry_id, user_id)
        if entry is None:
            return None
        entry.payload = data.payload
        await self.db.flush()
        return entry

    async def delete_entry(self, entry_id: str, user_id: str) -> bool:
        entry = await self.get_entry(entry_id, user_id)
        if entry is None:
            return False
        await self.db.delete(entry)
        await self.db.flush()
        return True

    async def clone_to_section_instance(
        self, entry_id: str, user_id: str
    ) -> SectionInstance:
        entry = await self.get_entry(entry_id, user_id)
        if entry is None:
            raise ValueError(f"Library entry {entry_id} not found for user {user_id}")
        return SectionInstance(
            id=str(uuid.uuid4()),
            type=entry.kind,
            title=_derive_title(entry.payload, entry.kind),
            enabled=True,
            data=copy.deepcopy(entry.payload),
            style=None,
        )

    async def promote_cv_to_library(
        self, cv_id: str, user_id: str
    ) -> PromoteResult:
        """Promote every Library-eligible section of a CV into Library entries.

        ``profile``/``summary`` (and any future non-eligible types) are
        reported in ``skipped``. Idempotent via content hash.
        """
        cv_result = await self.db.execute(
            select(CV).where(CV.id == cv_id, CV.user_id == user_id)
        )
        cv = cv_result.scalar_one_or_none()
        if cv is None:
            raise ValueError(f"CV {cv_id} not found for user {user_id}")

        library = await self._get_or_create_library(user_id)

        existing_stmt = select(LibraryEntry.kind, LibraryEntry.payload).where(
            LibraryEntry.library_id == library.id
        )
        existing_rows = (await self.db.execute(existing_stmt)).all()
        existing_hashes: set[tuple[str, str]] = {
            (row.kind, _content_hash(row.payload or [])) for row in existing_rows
        }

        sections = cv.sections or []
        if isinstance(sections, dict):
            sections = sections.get("sections", [])
        promoted: dict[str, int] = {}
        skipped: list[str] = []
        for section in sections or []:
            section_type = section.get("type") if isinstance(section, dict) else None
            if section_type not in LIBRARY_ENTRY_KINDS:
                if isinstance(section, dict) and section.get("id"):
                    skipped.append(section["id"])
                continue
            payload = section.get("data") if isinstance(section, dict) else None
            if not isinstance(payload, list):
                skipped.append(section.get("id", ""))
                continue
            h = _content_hash(payload)
            if (section_type, h) in existing_hashes:
                continue
            entry = LibraryEntry(library_id=library.id, kind=section_type, payload=payload)
            self.db.add(entry)
            existing_hashes.add((section_type, h))
            promoted[section_type] = promoted.get(section_type, 0) + 1
        await self.db.flush()
        return PromoteResult(library_id=library.id, promoted=promoted, skipped=skipped)
