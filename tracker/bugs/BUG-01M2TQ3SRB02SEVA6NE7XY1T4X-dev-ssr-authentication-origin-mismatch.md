---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M2TQ3SRB02SEVA6NE7XY1T4X
TYPE: bug
STATUS: DONE
PRIORITY: Medium
SEVERITY: Medium
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS:
- csrf
- authentication
- dev
RELATIONS: null
AFFECTS:
  files:
  - dev.sh
  - api/tests/test_devscript.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-18T16:55:35.947471+00:00'
UPDATED_AT: '2026-09-18T16:55:35.947471+00:00'
---

# Dev SSR authentication origin mismatch

## Background

The dev launcher supplied 127.0.0.1:5173 to TanStack Start while FastAPI trusted the configured localhost:5173 origin, causing authenticated SSR session resolution to return CSRF 403 responses when the CSRF cookie was absent.

## Investigation

FastAPI applies its CSRF guard to mutating API requests that carry an access
or refresh cookie. The dev launcher used `http://127.0.0.1:5173` as the SSR
fallback origin while the local API configuration used
`http://localhost:5173`. An authenticated SSR `POST /api/v1/auth/resolve`
could therefore be rejected before the endpoint could clear stale cookies.

## Decision

Derive one frontend origin after loading `.env`, export it as `FRONTEND_URL`
for FastAPI, and pass the same value to TanStack Start.

## Implementation

Updated `dev.sh` and added a launcher regression assertion covering the shared
origin contract.

## Verification

`bash -n dev.sh scripts/smoke.sh`, `git diff --check`,
`.venv/bin/pytest --noconftest -q tests/test_devscript.py` (7 tests), and a
focused ASGI request check pass. The stale-auth-cookie request now resolves as
anonymous instead of returning CSRF 403 when the configured origin matches.

## Follow-up
