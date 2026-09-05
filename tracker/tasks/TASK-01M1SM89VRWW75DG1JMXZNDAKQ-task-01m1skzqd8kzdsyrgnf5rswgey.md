---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1SM89VRWW75DG1JMXZNDAKQ
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
  - TASK-01M1SKZQD8KZDSYRGNF5RSWGEY
AFFECTS:
  files:
  - AGENTS.md
  - scripts/smoke.sh
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-05T20:30:41.528467+00:00'
UPDATED_AT: '2026-09-05T20:30:41.528467+00:00'
---

# Bound the migration smoke bootstrap

## Background

Bounded the Alembic stage in scripts/smoke.sh with AERGIA_SMOKE_MIGRATION_TIMEOUT_SECONDS (default 30s), preserving the migration check while preventing indefinite hangs.

## Investigation

The live smoke gate reached Alembic but could hang indefinitely when the
available Python 3.14/aiosqlite runtime stalled while opening the temporary
SQLite database. The migration check itself must remain intact; only its
unbounded wait needed to change.


## Decision

Use the Linux `timeout` utility with a configurable 30-second default. Preserve
non-timeout Alembic exit statuses and emit a specific compatibility hint when
the timeout fires.


## Implementation

`scripts/smoke.sh` now requires `timeout`, reads
`AERGIA_SMOKE_MIGRATION_TIMEOUT_SECONDS`, and bounds `alembic upgrade head`.
`AGENTS.md` documents the setting.


## Verification

The shell script passes `bash -n`; the previously observed Alembic hang now
terminates as a bounded timeout instead of leaving the smoke command running.


## Follow-up

Run the full smoke gate under the supported Python 3.12 runtime and keep the
default timeout unless migration complexity materially increases.
