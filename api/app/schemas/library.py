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


class AddEntryToLibraryResponse(BaseModel):
    """Response shape for ``POST /cvs/{cv_id}/sections/.../add-to-library``.

    ``created=False`` means an identical Library entry already exists
    (same kind + content hash); the FE should treat this as a no-op
    success. ``entry_id`` is the new or existing Library entry's id.
    """

    library_id: str
    entry_id: str | None
    created: bool


class AddEntryToLibraryRequest(BaseModel):
    """Current CV entry snapshot submitted by the builder.

    The builder uses manual saves, so the visible entry can be newer than
    the copy persisted on the CV. The section kind is included so a newly
    added, not-yet-saved section can still be routed correctly.
    """

    kind: LibraryEntryKind
    entry: dict




__all__ = [
    "LIBRARY_ENTRY_KINDS",
    "LIBRARY_KIND_TO_SECTION_TYPE",
    "SECTION_TYPE_TO_LIBRARY_KIND",
    "AddEntryToLibraryRequest",
    "AddEntryToLibraryResponse",
    "LibraryEntryCreate",
    "LibraryEntryKind",
    "LibraryEntryResponse",
    "LibraryEntryUpdate",
    "LibraryCloneResponse",
    "PromoteToLibraryResponse",
    "library_kind_for_section_type",
    "section_type_for_library_kind",
]


# Tuple form for membership checks (mirrors the Literal in app.schema.models).
LIBRARY_ENTRY_KINDS: tuple[LibraryEntryKindStr, ...] = tuple(
    kind.value for kind in LibraryEntryKind
)

# CV sections use plural names for four entry-based sections while Library
# rows use singular kinds. Keep the translation at this boundary so every
# service operation handles the same vocabulary.
SECTION_TYPE_TO_LIBRARY_KIND: dict[str, LibraryEntryKindStr] = {
    "experience": "experience",
    "education": "education",
    "skills": "skill",
    "projects": "project",
    "languages": "language",
    "certifications": "certification",
    # Accept legacy singular section names while old CV rows are migrated
    # naturally through the next write.
    "skill": "skill",
    "project": "project",
    "language": "language",
    "certification": "certification",
}
LIBRARY_KIND_TO_SECTION_TYPE: dict[str, str] = {
    "experience": "experience",
    "education": "education",
    "skill": "skills",
    "project": "projects",
    "language": "languages",
    "certification": "certifications",
}


def library_kind_for_section_type(section_type: str) -> LibraryEntryKindStr | None:
    return SECTION_TYPE_TO_LIBRARY_KIND.get(section_type)


def section_type_for_library_kind(kind: str) -> str | None:
    return LIBRARY_KIND_TO_SECTION_TYPE.get(kind)
