---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN9S
TYPE: feature
STATUS: IN_PROGRESS
SUMMARY: Drag-drop zone authoring — the customize tab lets users split, resize, create,
  and delete zones via the layout editor.
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: riasat
CONFIDENCE: High
TAGS:
- phase-6
- layout
- drag-drop
- zones
RELATIONS:
  part_of:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN7Y
AFFECTS:
  files:
  - web/src/components/layout/SectionZoneView.tsx
  - web/src/components/layout/ZoneStyleEditor.tsx
  - web/src/components/layout/ZoneCreationModal.tsx
  - web/src/pages/BuilderPage.tsx
  - web/src/lib/sections/zones.ts
  - web/src/components/__tests__/SectionZoneView.test.tsx
LINKS:
  plan: local://phase-6-content-only-authoring-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: 2026-08-08
UPDATED_AT: 2026-08-08
---

# Phase 6 step 3 — Drag-drop zone authoring

## Background

The customize tab already mounts `SectionZoneView` (`web/src/components/customization/CustomizePanel.tsx:362`) with `readOnly={false}`. The view implements the full zone authoring surface:
- **Zone reorder** via DnD with `horizontalListSortingStrategy` (`SectionZoneView.tsx:286-292`)
- **Section reorder / cross-zone move** via DnD with `SortableContext` per zone (`SectionZoneView.tsx:296-345`)
- **Unassigned drop area** for sections with no placement (`SectionZoneView.tsx:299-305`)
- **Zone create** via `ZoneCreationModal` triggered by an Add Zone button (`SectionZoneView.tsx:485-489`)
- **Zone delete** via per-zone delete control (`SectionZoneView.tsx:637`)
- **Zone style edit** via `ZoneStyleEditor` invoked per zone (`SectionZoneView.tsx:550-560`)

The handlers are wired through `BuilderPage` (`handleLayoutConfigChange`, `handleAddSection`, `handleRemoveInstance`, etc.) and persist via `PATCH /cvs/{id}` on save.

## Decision

The editor surface is already complete. The remaining work is verification: prove the round-trip works end-to-end (customize → preview → save → reload) and that the customize tab surfaces the zone authoring controls visibly.

## Implementation

- Add a BuilderPage integration test that exercises the round trip: select a CV with a template that has 2 zones, click the customize tab, simulate zone drag, assert `handleLayoutConfigChange` fires with the new ordering, save, reload, assert the new layout persists.
- Verify the customize panel still mounts `SectionZoneView` (existing test coverage).
- Add a test that creates a third zone via `ZoneCreationModal` and asserts the new zone is in the layout config with width normalization.

## Verification

```bash
cd web && npm test -- --run src/components/__tests__/SectionZoneView.test.tsx
# expect: existing tests + new round-trip tests pass
```

## Follow-up

None — this is the last editor-side behavior in the trimmed Phase 6 umbrella. With Steps 1, 2, 3 complete, the umbrella Phase 6 closes.

<!-- Migrated from FEAT-01KZPHASE6STEP3 during the schema-4 cutover. -->
