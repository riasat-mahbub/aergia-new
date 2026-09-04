---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1PQG1W7DZQN6095J4CB7VPG
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
  - web/src/pages/LibraryPage.tsx
  - web/src/components/library/
  - web/src/components/profile/ProfileCard.tsx
  - web/src/pages/__tests__/
  - web/src/components/library/__tests__/
  - web/src/main.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T17:29:37.927749+00:00'
UPDATED_AT: '2026-09-04T17:29:37.927749+00:00'
---

# Library page ownership

## Background

Step 4. Move LibraryPage and library-page composition into a page feature boundary. Keep the shared section/profile editor subsystem intact. Parent plan: FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT.

## Investigation


## Decision


## Implementation

- Move Library-page-only composition to `web/src/features/library/`.
- Keep shared profile/section-editor pieces and generic UI primitives in their existing boundaries.
- Update only the Library route import and affected relative paths.


## Verification


## Follow-up
