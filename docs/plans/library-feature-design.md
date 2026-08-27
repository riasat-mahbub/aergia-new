# Library Feature — Design Spec

**Status**: Proposed
**Date**: 2026-08-26
**Author**: brainstorming session

## Problem

Today, each `CV` row owns its full content: every experience, every education entry, every skill is duplicated per CV. A user with 3 CVs targeted at different roles retypes the same job history 3 times. Editing an experience in CV-A leaves CV-B silently stale.

The user wants a quality-of-life solution that makes creating new CVs faster, without restructuring the renderer, the templates, or the per-CV data model. CVs remain independent.

## Solution

Introduce a **Library**: a per-user store of typed reusable content entries (experiences, education, skills, projects, certifications, languages) that the user fills once and draws from when building or editing CVs. Copying a Library entry into a CV is a **structural copy** — once copied, the entry lives in the CV alone. The Library is purely an authoring aid; the render path is unchanged.

The Library's name avoids the existing `profile` section type and the existing `User` (auth) entity — both already taken.

## Non-Goals

- Live references / cross-CV sync (would require render-path changes; revisit if users ask).
- Library-aware templates or render features.
- AI auto-tailoring, suggestion engines, or bulk transformations.
- Sharing libraries across users.
- Versioning or change history for Library entries.

## Design

### Data Model

Two new tables. One `Library` per user (auto-created on first write). Library holds many `LibraryEntry` rows typed by `kind`.

```
Library
  id              uuid PK
  user_id         uuid FK users.id (UNIQUE, ON DELETE CASCADE)
  created_at      timestamptz
  updated_at      timestamptz

LibraryEntry
  id              uuid PK
  library_id      uuid FK libraries.id (ON DELETE CASCADE)
  kind            text  CHECK in ('experience','education','skill','project','certification','language')
  payload         JSONB
  created_at      timestamptz
  updated_at      timestamptz

  INDEX (library_id, kind)
```

`payload` mirrors the corresponding `SectionInstance.data` shape 1:1:
- For entry-based sections (`experience`, `education`, etc.), `payload` is a `list[EntryPayload]` where each element is a `SectionInstance.data` item (the `key`/`value`/`runs` shape the existing builders expect).
- This keeps "Add to CV" as a structural copy with a fresh `SectionInstance.id` stamped on the wrapper.

Validation uses `extra="ignore"` on the Pydantic read path so that older Library payloads remain readable if `SectionInstance.data` gains new optional fields. Unknown `kind` values are rejected at write time.

### Wire Schema (additive)

New file `api/app/schemas/library.py`:

```python
class LibraryEntryKind(str, Enum):
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILL = "skill"
    PROJECT = "project"
    CERTIFICATION = "certification"
    LANGUAGE = "language"

class LibraryEntryCreate(BaseModel):
    kind: LibraryEntryKind
    payload: list[dict]  # mirrors SectionInstance.data for entry-based sections

class LibraryEntryUpdate(BaseModel):
    payload: list[dict]

class LibraryEntryResponse(BaseModel):
    id: str
    kind: LibraryEntryKind
    payload: list[dict]
    created_at: datetime
    updated_at: datetime

class LibraryCloneResponse(BaseModel):
    """A SectionInstance-shaped JSON ready to drop into a CV's sections list."""
    section_instance: SectionInstance
```

`SectionInstance` is imported from `app.schema.models` — no schema duplication.

### API Surface

All routes mounted under `/api/v1/library` (singular to match `/templates`, `/cvs`):

```
GET    /library?kind={kind}        # list entries (all kinds if ?kind= omitted)
POST   /library                    # create entry
GET    /library/{id}               # read one
PATCH  /library/{id}               # update payload
DELETE /library/{id}               # delete (no CV effect; CVs retain their copies)
POST   /library/{id}/clone         # returns { section_instance: {...} } — ready to paste
```

One additional route on `/cvs`:

```
POST   /cvs/{cv_id}/promote-to-library
```

This extracts every section from the CV whose `type` matches a `LibraryEntryKind`, generates a `LibraryEntry` per section, and returns `{ promoted: {kind: count}, library_id: str }`. Existing CV is unchanged.

Behaviour details:
- Library rows auto-created per user on first write (service-layer `get_or_create_library(user_id)`).
- `DELETE /library/{id}` is a hard delete; CV copies are unaffected (intentional — that's the QOL contract).
- `PATCH /library/{id}` only mutates the Library row; CV copies are unaffected.
- `promote-to-library` is idempotent on the CV (running twice produces duplicates — user can dedupe manually in v1).

### Service Layer

`api/app/services/library.py` mirrors `cv.py` shape:

```python
class LibraryService:
    def __init__(self, db: AsyncSession): ...

    async def _get_or_create_library(self, user_id: str) -> Library: ...
    async def list_entries(self, user_id: str, kind: LibKind | None = None) -> list[LibraryEntry]: ...
    async def create_entry(self, user_id: str, data: LibraryEntryCreate) -> LibraryEntry: ...
    async def get_entry(self, entry_id: str, user_id: str) -> LibraryEntry | None: ...
    async def update_entry(self, entry_id: str, user_id: str, data: LibraryEntryUpdate) -> LibraryEntry | None: ...
    async def delete_entry(self, entry_id: str, user_id: str) -> bool: ...
    async def clone_to_section_instance(self, entry_id: str, user_id: str) -> SectionInstance: ...
    async def promote_cv_to_library(self, cv_id: str, user_id: str) -> PromoteResult: ...
```

`clone_to_section_instance` builds a `SectionInstance` with:
- `id`: fresh UUID
- `type`: `entry.kind` value (so the existing builder dispatch works unchanged)
- `title`: derived from payload (e.g. first `title` field, or `kind` capitalized)
- `enabled`: True
- `data`: `entry.payload` copied verbatim
- `style`: None (no per-entry styling in Library)

### Renderer Impact

**None.** The Renderer pipeline (`build_document` → `resolve` → `HTMLDocumentRenderer`) reads only from the CV row. Library entries never appear in the render path. Confirmed by reading `SectionInstance` data flow: `CV.sections` JSONB → `SectionInstance` list → builders dispatch on `type` → resolved `Document` → renderer. Library lives upstream of CV creation only.

### Frontend

**New store** `web/src/lib/store/libraryStore.ts` (Zustand):
- `entries: LibraryEntry[]`, `byKind: Map<kind, LibraryEntry[]>`, `loaded: boolean`
- `fetchAll()`, `create()`, `update()`, `remove()`, `cloneToSection(entryId)` (returns a `SectionInstance` shape; consumer appends to `cvStore.currentCv.sections`)

**New routes**:
- `/library` — full Library manager page (grid grouped by kind, create/edit/delete modals reusing existing field editors from `web/src/components/sections/`).

**New components**:
- `<LibraryDrawer>` — collapsible side drawer on the CV builder. Lists library entries by kind. Each entry has an "Add to this CV" button. On click: call `cloneToSection`, append result to `cvStore.currentCv.sections`, mark CV dirty, toast "Added [title] to [section]".
- `<PromoteToLibraryButton>` — on the CV card menu (dashboard) and the builder header. Calls `promote-to-library`; toast shows counts; offers "Open Library" link.

**Codegen**: `web/src/generated/schema.ts` regenerates from `app.schema.models`. New types `LibraryEntryKind`/`LibraryEntryResponse`/etc. are added via the existing codegen path. No manual TS edits.

### Migration

None required. New tables, new routes, no DB column changes to existing tables. Backward compatible — users without any Library entries see no UI changes until they explicitly visit `/library` or use `<PromoteToLibraryButton>`.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `SectionInstance.data` shape evolves; old Library payloads become invalid | Pydantic `extra="ignore"` on read; validators only check structural invariants not exhaustive field lists |
| Users confused why editing Library doesn't update CV | Empty-state copy and tooltips: "The Library is your reusable content. Add an entry to a CV to use it there." |
| Library grows unbounded with duplicates | Out of scope for v1; document as future work. Users can delete manually. |
| `promote-to-library` creates duplicates on re-run | Documented; future enhancement: dedupe by content hash |
| Accidental Library deletion | Soft-delete deferred; v1 is hard delete with confirmation toast |
| Naming collision with existing `profile` section | Library has no entry kind called `profile`; the closest semantic is `summary` (separate kind). The CV's profile section is still authored directly in the CV (small per-CV data; doesn't fit the Library model). |

## Testing

### Backend (pytest)
- `tests/test_library.py`:
  - `test_library_auto_created_on_first_write`
  - `test_create_list_update_delete_entry`
  - `test_clone_returns_section_instance_with_fresh_id`
  - `test_clone_is_isolated_from_library_edits`
  - `test_delete_does_not_affect_cv_copies`
  - `test_promote_cv_to_library_extracts_sections`
  - `test_promote_is_idempotent_on_cv_side`
  - `test_user_cannot_access_other_users_library`
  - `test_unknown_kind_rejected`
  - `test_clone_payload_matches_section_instance_data_shape`
  - `test_library_unaffected_by_renderer` (smoke: build_document does not touch library table)

### Frontend (Vitest)
- `web/src/lib/store/__tests__/libraryStore.test.ts`:
  - CRUD operations
  - clone returns SectionInstance with new id
  - byKind grouping
- `web/src/components/library/__tests__/LibraryDrawer.test.tsx`:
  - renders entries by kind
  - "Add to this CV" appends to cvStore
  - empty state copy
- `web/src/components/library/__tests__/PromoteToLibraryButton.test.tsx`:
  - calls API and shows counts toast

### Smoke
- `./dev.sh --smoke` continues to pass; no change to smoke flow.

## Open Questions

None — design locks the constraints from brainstorming:
- Snapshot at link time (CVs stay independent).
- Library is authoring-only; render path unchanged.
- Name: Library (avoids "profile" collision).
- UI surface: drawer + dashboard card + dedicated page.
- Migration: opt-in per CV via Promote button.

## Follow-up (deferred, not in this spec)

- Bulk import (LinkedIn CSV, JSON Resume).
- Library-wide search / filter by tag.
- Duplicate detection on promote.
- "Used in N CVs" counter per Library entry.
- Per-entry tags/categories.
- Soft delete + restore.
