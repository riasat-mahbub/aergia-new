---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1SKZQD8KZDSYRGNF5RSWGEY
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01M1SCABVERF1TSZRVF5N5PDCP
AFFECTS:
  files:
  - AGENTS.md
  - api/tests/test_cleanup_application_artifacts.py
  - api/tests/test_gliner2_spike.py
  - api/tests/test_smoke_live.py
  - scripts/smoke.sh
  - web/src/middleware/security/contentSecurityPolicy.ts
  - web/src/middleware/security/nonce.ts
  - web/src/middleware/security/securityHeaders.ts
  - web/src/middleware/security/securityMiddleware.ts
  - web/src/middleware/security/types.ts
  - web/src/router.tsx
  - web/src/start.ts
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-05T20:26:00.488739+00:00'
UPDATED_AT: '2026-09-05T20:26:00.488739+00:00'
---

# TanStack Start migration hardening

## Background

Implemented the migration hardening plan: removed three stale tests that referenced deleted scripts, deferred the legacy pytest suite, added segmented TanStack Start security middleware with nonce CSP and CSRF protection, propagated the nonce into SSR scripts, and expanded the smoke gate for headers, nonce reuse prevention, auth cookies, and Start/FastAPI integration. Static checks and an isolated mock-API SSR check pass; the live Alembic stage remains blocked by the existing Python 3.14/aiosqlite hang.

## Investigation

The migration no longer has the deleted `api/scripts/smoke_live.py` or the two
spike/cleanup script modules referenced by three old test files. Those tests
could not collect without being rewritten, so they are removed under the
agreed deferred-test-suite rule. The remaining checks are retained unchanged.

The Start instance was custom-created, so its request middleware list had to
include CSRF protection explicitly. A security middleware boundary was also
needed to generate a nonce before SSR and to make the nonce available to
TanStack Router's script rendering. The live API-backed smoke could not pass
the Alembic bootstrap in this environment because Python 3.14/aiosqlite hangs
while opening the fresh SQLite database.

## Decision

Use TanStack Start request middleware for application security and keep Nitro
limited to the same-origin FastAPI gateway. Defer the comprehensive test-suite
rewrite and all deployment changes. Do not trust forwarded HTTPS headers until
the public proxy is explicitly configured.


## Implementation

- Added `web/src/middleware/security/` for nonce generation, CSP construction,
  security headers, Start request context typing, and request middleware.
- Registered Start CSRF middleware in `web/src/start.ts` and passed the
  per-request nonce into router SSR options.
- Removed three stale test modules that referenced deleted scripts.
- Updated `scripts/smoke.sh` to omit the deferred pytest suite and verify SSR,
  nonce propagation/rotation, security headers, gateway routing, login, and
  root-scoped auth cookies.
- Updated `AGENTS.md` to describe the migration smoke gate and deferred tests.


## Verification

- `npm run typecheck` passed.
- `npm run build` passed.
- `npm run lint` passed with 11 pre-existing warnings and zero errors.
- `npm run architecture:check` passed.
- `npm run architecture:test` passed.
- `npm run codegen:check` passed.
- `api/.venv/bin/ruff check app tests` passed.
- An isolated Start server with a mock API returned SSR HTML with matching
  nonce attributes and different nonces on consecutive requests.
- Full `scripts/smoke.sh` execution remains blocked at `alembic upgrade head`
  by the known Python 3.14/aiosqlite hang.


## Follow-up

Run the deferred replacement test suite and the live migration/auth smoke under
the supported Python 3.12 environment. Decide forwarded-proxy trust and HSTS
deployment behavior when deployment work is scheduled.
