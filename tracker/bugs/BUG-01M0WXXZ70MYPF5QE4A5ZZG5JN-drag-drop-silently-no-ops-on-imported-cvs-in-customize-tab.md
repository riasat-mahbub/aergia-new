---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M0WXXZ70MYPF5QE4A5ZZG5JN
TYPE: bug
STATUS: PROPOSED
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: riasat
CONFIDENCE: High
TAGS:
- renderer
- parser
- drag-drop
- regression
RELATIONS: null
AFFECTS:
  files:
  - web/src/components/layout/SectionZoneView.tsx
  - api/app/services/parser/mapper.py
  - api/scripts/migrate_imported_ids_to_sec_prefix.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-25T17:01:50.176759+00:00'
UPDATED_AT: '2026-08-25T17:01:50.176759+00:00'
---

# Drag-drop silently no-ops on imported CVs in Customize tab

## Background

User reported that on the imported CV `bfb39c1f-81fe-4fd4-b66c-c5a034aa80cf`
(plus every other imported CV in the dev DB), the Customize tab's
"Layout" pane showed all sections as "not assigned to any zone". Dragging
sections onto a zone visually moved them, but the drop was discarded —
the unassigned count never went down.

Two compounding causes:

1. `SectionZoneView.handleDragEnd` early-returns for any `active.id` that
   doesn't start with the `sec_` prefix, delegating to `onEntryDragEnd`.
   The Customize panel passes `() => {}` for that handler.
2. The PDF parser emitted type-specific prefixes (`prof_`, `edu_`, `exp_`,
   `skg_`, `proj_`, `cert_`, `lang_`, `res_`, `ext_`, `imp_`) for every
   section and entry id, violating the implicit `sec_*` contract.

## Investigation

- `web/src/components/layout/SectionZoneView.tsx:280-283` contained:
  ```ts
  if (!activeId.startsWith("sec_")) {
    onEntryDragEnd(event);
    return;
  }
  ```
- `api/app/services/parser/mapper.py:52-53` defined
  `_new_id(prefix: str = "imp")` and emitted e.g. `prof_<hex>` from each
  section type's builder call site.
- Survey of the dev DB: 7 of 13 active CVs held non-`sec_` ids (the
  parser's `prof_*`, `edu_*`, `sk_*`, `skg_*`, `proj_*`, `cert_*`,
  `lang_*`, `res_*`, `ext_*` prefixes). Two CVs that shared section
  content via Copy (`bfb39c1f` "Resume (Copy)" + `ccb4ae29` "Target CV
  Clone") carried identical id sets — even if we'd patched the guard,
  the duplication would have collided on a global rewrite.
- dnd-kit's gesture layer still triggered drag visuals, but
  `handleDragEnd` returned immediately on the prefix mismatch, so the
  `onLayoutConfigChange` call (which carries the new placement entry)
  was never made.

## Decision

Two-part fix:

1. **Drop the prefix guard.** Entry-level DnD is not currently rendered
   in `SectionZoneView` (only section-level `useSortable`s are
   registered here), and the `sec_` heuristic is an implicit contract
   that the parser violates. Every drop in this component is a
   section drop; route it through the existing placement logic. The
   `onEntryDragEnd` prop stays in the signature for the future feature
   the comment anticipated, but no caller passes a real handler today
   (CustomizePanel passes `() => {}`).
2. **Fix the parser** so it emits `sec_<hex>` for every section and
   entry id. Drop the per-type tag from `_new_id` and from
   `_build_simple_entries`'s `prefix` parameter — type information
   lives in `SectionInstance.type` and `entry` shape, not in the id.
3. **One-shot data migration** so existing imported CVs also gain
   `sec_` ids. The migration script generates fresh `sec_<hex>` ids per
   CV (not globally) so two CVs that previously shared ids (copy of a
   copy) end up with distinct ids.

## Implementation

- `web/src/components/layout/SectionZoneView.tsx`: replaced the prefix
  guard + `onEntryDragEnd(event); return;` with a comment explaining
  the simplification. Every drop now reaches the placement logic.
- `api/app/services/parser/mapper.py`:
  - `_new_id` now returns `sec_{uuid.uuid4().hex[:8]}` with no
    per-type tag.
  - All 14 call sites updated (`_new_id("prof")` → `_new_id()` etc.).
  - `_build_simple_entries` lost its `prefix` parameter; the three
    callers (projects, certifications, research) updated.
- `api/scripts/migrate_imported_ids_to_sec_prefix.py`: one-shot script
  that walks each CV's `sections` and `customizations` JSON, builds a
  per-CV `{old_id: new_id}` map using `secrets.token_hex(4)`,
  rewrites every `id` value and every key that matches an old id
  (covering `placement` and `per_section` dicts), and commits. Idempotent
  and `--dry-run` by default.

## Verification

- `api/tests/test_parser_imports.py tests/test_parsers.py
  tests/test_parser_keys.py tests/test_parser_providers.py
  tests/test_parser_strategies.py tests/test_parser_orchestrator.py
  tests/test_extract_fonts.py tests/test_parser_smoke.py`: 101 passed.
- Migration applied to dev DB: 7 CVs migrated, 149 id rewrites. Survey
  after migration: `No CVs with legacy IDs found`. Two CVs that
  previously shared section ids (`bfb39c1f` Resume (Copy) and
  `ccb4ae29` Target CV Clone) now have distinct `sec_*` ids per CV.
- Browser smoke against the migrated `ccb4ae29` CV in the Customize
  tab: dragged `sec_dcfb43b6` from unassigned into the `main` zone;
  `inZone` count went from 0 to 1, unassigned count from 6 to 5. The
  fix is end-to-end.
- Full backend test suite: 353 passed, 4 failed (all pre-existing
  failures unrelated to this change: `test_auth_full_flow`,
  `test_register_duplicate_email`, `test_cv_crud_flow`,
  `test_seed_manifests_use_constrained_vocabulary`).

## Follow-up

The migration script is intentionally idempotent so it can be re-run
on staging / production DBs without further changes. New imports after
this commit use the new `_new_id` shape automatically — no migration
needed for fresh data.

Consider adding a schema-level guard (Alembic + Pydantic validator) on
`SectionInstance.id` to enforce the `sec_` prefix at the wire boundary,
so this implicit contract can't quietly regress again.