---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1PQG28944A85QPJ1P2AAQTE
TYPE: task
STATUS: PLANNED
PRIORITY: Medium
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT
AFFECTS:
  files:
  - web/src/pages/BuilderPage.tsx
  - web/src/components/builder/
  - web/src/components/customization/
  - web/src/components/preview/
  - web/src/components/sections/
  - web/src/pages/__tests__/BuilderPage.handleUpdateStyle.test.ts
  - web/src/main.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T17:29:38.313863+00:00'
UPDATED_AT: '2026-09-04T17:29:38.313863+00:00'
---

# Builder page ownership

## Background

Step 6. Move BuilderPage and builder-only composition into a page feature boundary. Treat preview, customization, and section editing as shared or separately owned subsystems until their actual consumers are verified. Parent plan: FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT.

## Investigation


## Decision


## Implementation

- Move Builder-page-only orchestration to `web/src/features/builder/`.
- Audit, but do not automatically move, preview, customization, and section-editor subsystems because they have cross-page consumers.
- Preserve the save blocker, iframe preview, PDF export, and route behavior.


## Verification


## Follow-up
