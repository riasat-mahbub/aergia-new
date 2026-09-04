---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1PQG3ASA896YTGP9RDTAQG0
TYPE: task
STATUS: PLANNED
PRIORITY: Medium
SEVERITY: null
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT
AFFECTS:
  files:
  - web/src/pages/NotFoundPage.tsx
  - web/src/main.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T17:29:39.417079+00:00'
UPDATED_AT: '2026-09-04T17:29:39.417079+00:00'
---

# Not-found page ownership

## Background

Step 12. Move NotFoundPage into the page feature boundary and verify the wildcard route, links, and fallback behavior. Parent plan: FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT.

## Investigation


## Decision


## Implementation

- Move wildcard fallback composition to `web/src/features/not-found/`.
- Verify the fallback route and its navigation links remain unchanged.


## Verification


## Follow-up
