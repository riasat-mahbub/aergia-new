---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KZPHASE6STEP2-PANEL
TYPE: task
STATUS: PROPOSED
SUMMARY: 'Frontend test asserts the customize panel writes per-instance policy overrides through the wire.'
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: riasat
CONFIDENCE: High
TAGS:
- phase-6
- frontend
- customize-panel
RELATIONS:
  part_of:
    - FEAT-01KZPHASE6STEP2
AFFECTS:
  files:
    - web/src/components/customization/CustomizePanel.tsx
    - web/src/components/__tests__/CustomizePanel.test.tsx
LINKS:
  plan: local://phase-6-content-only-authoring-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: 2026-08-08
UPDATED_AT: 2026-08-08
---

# CustomizePanel writes per-instance SectionPolicy

## Background

The customize panel's "Section policy" disclosure (in `web/src/components/customization/CustomizePanel.tsx:600-633`) already exposes `show_title` and `skill_variant` controls that write through `onUpdateStyle` → `handleUpdateStyle`. The wire carries `style.policy.{show_title, skill_variant}`.

## Decision

Add a regression test that asserts the customize panel actually writes per-instance `policy` overrides, not just type-level ones. The existing test for skills_layout exists but is per-type (skills variant). Add an explicit test that selects two skills instances and verifies each carries its own `policy` after the panel writes.

## Implementation

Add a test in `web/src/components/__tests__/CustomizePanel.test.tsx`:

```ts
it("writes per-instance policy override that supersedes the type default", () => {
  // Two skills instances; first gets skill_variant=block, second gets skill_variant=inline
  // Assert that onUpdateStyle is called with the per-instance policy for each
});
```

Use the existing CustomizePanel test harness; the test mocks `onUpdateStyle`. Verify both writes carry a `policy` field with the expected `skill_variant`.

## Verification

```bash
cd web && npm test -- --run src/components/__tests__/CustomizePanel.test.tsx
# expect: existing tests + 1 new test pass
```

## Follow-up

None.
