---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1PQG2Z4V4Z0KHRQGFNZ7X6G
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
  - web/src/pages/RegisterPage.tsx
  - web/src/components/auth/RegisterForm.tsx
  - web/src/components/auth/TurnstileWidget.tsx
  - web/src/components/__tests__/RegisterForm.test.tsx
  - web/src/main.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T17:29:39.045009+00:00'
UPDATED_AT: '2026-09-04T17:29:39.045009+00:00'
---

# Register page ownership

## Background

Step 10. Move RegisterPage and registration-only composition into a page feature boundary; preserve Turnstile and auth behavior. Parent plan: FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT.

## Investigation


## Decision


## Implementation

- Move registration-page composition to `web/src/features/register/`.
- Keep Turnstile integration client-only and preserve registration behavior.


## Verification


## Follow-up
