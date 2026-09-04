---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1PQG1P0N29M8A9Z52TV0BP9
TYPE: task
STATUS: PLANNED
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT
AFFECTS:
  files:
  - web/src/pages/ApplicationDetailPage.tsx
  - web/src/pages/__tests__/ApplicationDetailPage.test.tsx
  - web/src/components/applications/ApplicationFormModal.tsx
  - web/src/main.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T17:29:37.728898+00:00'
UPDATED_AT: '2026-09-04T17:29:37.728898+00:00'
---

# Application detail page ownership

## Background

Step 3. Move ApplicationDetailPage and detail-only composition into its page feature boundary. Preserve the shared application form and API contracts. Parent plan: FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT.

## Investigation


## Decision


## Implementation

- Move detail-only composition to `web/src/features/application-detail/`.
- Keep `ApplicationFormModal` at a shared boundary unless the import graph proves it is detail-only.
- Preserve the `/dashboard/applications/:id` route and API behavior.


## Verification


## Follow-up
