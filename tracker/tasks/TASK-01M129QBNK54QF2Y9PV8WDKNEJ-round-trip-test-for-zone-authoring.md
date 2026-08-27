---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNEJ
TYPE: task
STATUS: PROPOSED
SUMMARY: Add a BuilderPage round-trip test that exercises drag-drop zone authoring
  end to end.
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: riasat
CONFIDENCE: High
TAGS:
- phase-6
- frontend
- zones
- roundtrip
RELATIONS:
  part_of:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN9S
AFFECTS:
  files:
  - web/src/pages/BuilderPage.tsx
  - web/src/pages/__tests__/BuilderPage.handleLayoutConfigChange.test.tsx (new)
  - web/src/components/__tests__/SectionZoneView.test.tsx
LINKS:
  plan: local://phase-6-content-only-authoring-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: 2026-08-08
UPDATED_AT: 2026-08-08
---

# Round-trip test for zone authoring

## Background

`BuilderPage.handleLayoutConfigChange` writes through to `setLocalCustomizations` → save → `PATCH /cvs/{id}`. The customize tab invokes this through `CustomizePanel` → `SectionZoneView` → DnD handlers. No end-to-end test exercises the round trip from drag to saved CV.

## Decision

Add an integration test that drives the customize tab surface and asserts the wire flows correctly through BuilderPage's handlers.

## Implementation

Create `web/src/pages/__tests__/BuilderPage.handleLayoutConfigChange.test.tsx`:

- Mock `useAuthStore`, `useCVStore`, `useSupportStore`, `useNavigate`, `useBlocker`.
- Render `BuilderPage` with a fixture CV that has 2 zones and 3 sections.
- Switch to the customize tab.
- Find the SectionZoneView drag handles and simulate a zone reorder via DnD (or directly call the handler through the test harness).
- Assert `setHasUnsavedChanges(true)` and that the new layout config has the reordered zones.
- Click save and assert `updateCV` is called with the new layout.

If DnD is hard to drive from the test, use a direct handler call via the test harness — the surface is already wired and a handler-level test locks down the contract.

## Verification

```bash
cd web && npm test -- --run src/pages/__tests__/BuilderPage.handleLayoutConfigChange.test.tsx
# expect: new test passes
```

## Follow-up

None.

<!-- Migrated from TASK-01KZPHASE6STEP3-ROUNDTRIP during the schema-4 cutover. -->
