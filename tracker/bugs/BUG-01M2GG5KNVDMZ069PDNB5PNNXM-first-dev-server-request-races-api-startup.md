---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M2GG5KNVDMZ069PDNB5PNNXM
TYPE: bug
STATUS: DONE
PRIORITY: Medium
SEVERITY: Medium
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS:
  files:
  - dev.sh
  - api/tests/test_devscript.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-14T17:41:50.907326+00:00'
UPDATED_AT: '2026-09-14T17:41:50.907326+00:00'
---

# First dev-server request races API startup

## Background

The TanStack Start frontend can accept its first request before FastAPI finishes startup, so SSR session resolution fails until a reload.

## Investigation

`dev.sh` launched Uvicorn in the background and immediately started the
frontend. TanStack Start resolves the session from FastAPI during the root
route's SSR, so a request during FastAPI's startup could fail and succeed on a
later reload. FastAPI's `/readyz` endpoint checks database availability after
its startup lifespan has completed.

## Decision

Wait for `/readyz` to return HTTP 200 before starting either frontend mode.
Stop startup with a clear error if FastAPI does not become ready within 60
seconds.

## Implementation

Added a bounded readiness poll to `dev.sh`, with cleanup of the API process on
timeout. Added a launcher regression check that ensures readiness is checked
before frontend startup.

## Verification

`bash -n dev.sh scripts/smoke.sh`, `git diff --check`, and
`.venv/bin/pytest --noconftest -q tests/test_devscript.py` pass (6 tests).
The repository smoke gate built the frontend, but its temporary-database
Alembic migration timed out at both the default 30 seconds and an extended
120 seconds, before its live-server checks.

## Follow-up

None.
