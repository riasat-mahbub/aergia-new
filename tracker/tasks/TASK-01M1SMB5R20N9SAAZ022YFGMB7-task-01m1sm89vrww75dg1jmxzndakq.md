---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1SMB5R20N9SAAZ022YFGMB7
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
  - TASK-01M1SM89VRWW75DG1JMXZNDAKQ
AFFECTS:
  files:
  - AGENTS.md
  - scripts/smoke.sh
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-05T20:32:15.618826+00:00'
UPDATED_AT: '2026-09-05T20:32:15.618826+00:00'
---

# TASK-01M1SM89VRWW75DG1JMXZNDAKQ

## Background

Verified the bounded migration stage after restoring the API working directory: AERGIA_SMOKE_MIGRATION_TIMEOUT_SECONDS=1 exits 124 with the intended compatibility diagnostic.

## Investigation

The first bounded-smoke patch accidentally ran Alembic from the repository
root. The corrected command keeps the existing `api/` working directory and
only bounds its runtime.


## Decision

Keep the migration check authoritative, return Alembic's timeout status, and
make the compatibility failure actionable rather than silently bypassing it.


## Implementation

The smoke gate runs `(cd "$API_DIR" && timeout ... alembic upgrade head)` and
reports status 124 with the configured timeout when the async SQLite runtime
stalls.


## Verification

With `AERGIA_SMOKE_MIGRATION_TIMEOUT_SECONDS=1`, Ruff, frontend smoke ESLint,
and the production build pass; the live stage exits 124 with the intended
diagnostic and no process remains running.


## Follow-up

Re-run without the reduced timeout under Python 3.12/aiosqlite once the
runtime compatibility blocker is removed.
