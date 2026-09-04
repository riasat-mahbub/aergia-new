---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1PQG2SHP5H9A7SGK6DPHMNZ
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
  - web/src/pages/LoginPage.tsx
  - web/src/components/auth/LoginForm.tsx
  - web/src/components/__tests__/LoginForm.test.tsx
  - web/src/main.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T17:29:38.865974+00:00'
UPDATED_AT: '2026-09-04T17:29:38.865974+00:00'
---

# Login page ownership

## Background

Step 9. Move LoginPage and login-only composition into a page feature boundary; keep auth infrastructure and shared form primitives stable. Parent plan: FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT.

## Investigation


## Decision


## Implementation

- Move login-page composition to `web/src/features/login/`.
- Keep auth state, API client, and generic form infrastructure shared.
- Preserve login redirect and error behavior.


## Verification


## Follow-up
