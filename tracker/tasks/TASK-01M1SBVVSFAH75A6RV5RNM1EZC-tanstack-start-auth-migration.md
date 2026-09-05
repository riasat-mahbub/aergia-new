---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1SBVVSFAH75A6RV5RNM1EZC
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS:
- tanstack-start
- ssr
- auth
- cookies
- migration
RELATIONS: null
AFFECTS: null
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-05T18:04:05.295822+00:00'
UPDATED_AT: '2026-09-05T18:04:05.295822+00:00'
---

# tanstack-start-auth-migration

## Background

Replaced the Vite/React Router entry with TanStack Start + Nitro route modules; classified public SSR, guarded data-only, and client-heavy routes; added root-scoped HttpOnly cookie migration and POST /api/v1/auth/resolve; forwarded auth/cookies through Start SSR and a same-origin Nitro /api gateway; seeded a request-scoped Zustand auth store; updated dev/build/Docker Compose wiring and route compatibility imports. Verified build, typecheck, architecture checks, focused ruff/compile checks, and live SSR/login/refresh/logout smoke.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
