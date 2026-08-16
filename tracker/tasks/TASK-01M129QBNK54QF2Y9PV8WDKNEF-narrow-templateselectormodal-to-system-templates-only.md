---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNEF
TYPE: task
STATUS: PROPOSED
SUMMARY: Narrow TemplateSelectorModal to system-templates only; drop upload and delete
  affordances.
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: riasat
CONFIDENCE: High
TAGS:
- phase-6
- narrowing
RELATIONS:
  part_of:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN9Q
AFFECTS:
  files:
  - web/src/components/customization/TemplateSelectorModal.tsx
  - web/src/lib/api/templates.ts
LINKS:
  plan: local://phase-6-content-only-authoring-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: 2026-08-08
UPDATED_AT: 2026-08-08
---

# Narrow TemplateSelectorModal to system-templates only

## Background

The modal currently lists system templates, then user templates, then has a
file-upload affordance. After the user-template authoring surface is deleted,
the modal must show only system templates — Modern, Classic, Minimal.

## Decision

Delete the user-templates section, the file-upload block, and the delete
confirmation. Keep only the "System Templates" section. The modal becomes
~80 lines: a list of system templates with the active one highlighted, plus a
Cancel button.

Also drop the unused frontend API functions:
`fetchUserTemplates`, `uploadUserTemplate`, `deleteUserTemplate`, and the
`UserTemplateCreate` interface. `fetchSystemTemplates` keeps the
`.filter((t) => !t.is_user_template)` step removed (the field is gone).
`UserTemplate.is_user_template` is removed from the interface.

## Implementation

Plan §4.4 + §4.5.

## Verification

```bash
grep -rn "uploadUserTemplate\|deleteUserTemplate\|fetchUserTemplates\|is_user_template" web/src/
# expect: zero matches
cd web && npm test -- --run web/src/components/__tests__/CustomizePanel.test.tsx
# expect: pass; the panel still mounts the modal
```

## Follow-up

None.

<!-- Migrated from TASK-01KZPHASE6STEP1-MODAL during the schema-4 cutover. -->
