"""Library wire schema — request / response models for the Library endpoints.

The Library wire shape mirrors :class:`SectionInstance.data` for entry-based
section kinds. Type-aware data validation lives in ``app.schema`` (the AST
source of truth). HTTP I/O shapes stay here so codegen continues to pick up
the AST models while the service layer can validate incoming payloads
against the closed ``LibraryEntryKind`` enum.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from app.schema.models import LibraryEntryKindStr, SectionInstance


class LibraryEntryKind(str, Enum):
    """Closed set of entry-based section kinds eligible for the Library.

    The CV's ``profile`` and ``summary`` sections have dict-shaped
    ``SectionInstance.data`` and are excluded from Library promotion —
    they stay authored directly inside the CV.
    """

    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILL = "skill"
    PROJECT = "project"
    CERTIFICATION = "certification"
    LANGUAGE = "language"


class LibraryEntryCreate(BaseModel):
    """Request body to create a Library entry."""

    kind: LibraryEntryKind
    payload: list[dict] = []


class LibraryEntryUpdate(BaseModel):
    """Request body to mutate a Library entry's payload."""

    payload: list[dict]


class LibraryEntryResponse(BaseModel):
    """Response shape for a Library entry.

    ``model_config = {"from_attributes": True}`` lets the route return an
    ORM row directly; ``payload`` accepts the JSON column as a Python list.
    """

    model_config = {"from_attributes": True}

    id: str
    kind: LibraryEntryKind
    payload: list[dict]
    created_at: datetime
    updated_at: datetime


class LibraryCloneResponse(BaseModel):
    """Response shape for the clone endpoint.

    ``section_instance`` is a ready-to-paste ``SectionInstance`` that the
    CV builder can append to ``cvStore.currentCV.sections`` directly.
    """

    section_instance: SectionInstance


class PromoteToLibraryResponse(BaseModel):
    """Response shape for promoting a CV's entries into the Library.

    ``promoted`` maps each eligible kind to the number of new entries
    created on this call (excluding content-hash duplicates). ``skipped``
    lists section IDs whose ``type`` is not eligible (e.g. ``profile``)
    so the FE can surface them in a toast.
    """

    library_id: str
    promoted: dict[str, int]
    skipped: list[str]


__all__ = [
    "LIBRARY_ENTRY_KINDS",
    "LibraryEntryCreate",
    "LibraryEntryKind",
    "LibraryEntryResponse",
    "LibraryEntryUpdate",
    "LibraryCloneResponse",
    "PromoteToLibraryResponse",
]


# Tuple form for membership checks (mirrors the Literal in app.schema.models).
LIBRARY_ENTRY_KINDS: tuple[LibraryEntryKindStr, ...] = tuple(
    kind.value for kind in LibraryEntryKind
)
