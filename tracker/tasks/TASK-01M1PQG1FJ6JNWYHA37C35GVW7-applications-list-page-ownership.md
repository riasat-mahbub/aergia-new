---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1PQG1FJ6JNWYHA37C35GVW7
TYPE: task
STATUS: PLANNED
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT
AFFECTS:
  files:
  - web/src/pages/ApplicationsPage.tsx
  - web/src/components/applications/ApplicationCard.tsx
  - web/src/components/applications/applicationPresentation.ts
  - web/src/pages/__tests__/ApplicationsPage.test.tsx
  - web/src/components/applications/__tests__/applicationPresentation.test.ts
  - web/src/main.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T17:29:37.522667+00:00'
UPDATED_AT: '2026-09-04T17:29:37.522667+00:00'
---

# Applications list page ownership

## Background

Step 2. Move ApplicationsPage and list-only application UI into a page feature boundary. Keep ApplicationFormModal shared with application detail until reuse is re-evaluated. Parent plan: FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT.

## Investigation


## Decision


## Implementation

- Move list-only composition to `web/src/features/applications/`.
- Leave `ApplicationFormModal` shared with the detail page until its actual consumers are rechecked.
- Update only the Applications route import and affected relative paths.


## Verification


## Follow-up
