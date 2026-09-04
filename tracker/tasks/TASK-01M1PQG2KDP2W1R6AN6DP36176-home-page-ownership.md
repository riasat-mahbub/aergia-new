---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1PQG2KDP2W1R6AN6DP36176
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
  - web/src/pages/HomePage.tsx
  - web/src/main.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T17:29:38.669652+00:00'
UPDATED_AT: '2026-09-04T17:29:38.669652+00:00'
---

# Home page ownership

## Background

Step 8. Move HomePage and public-home-only composition into a page feature boundary while preserving the public route and auth links. Parent plan: FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT.

## Investigation


## Decision


## Implementation

- Move public-home composition to `web/src/features/home/`.
- Preserve the `/` route, auth links, and public-only behavior.


## Verification


## Follow-up
