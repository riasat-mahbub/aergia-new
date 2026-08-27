---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNBJ
TYPE: task
STATUS: PLANNED
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- plan
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T18:38:28.730318+00:00'
UPDATED_AT: '2026-08-01T18:38:28.730318+00:00'
---

# Fix the launch in dev.sh using a bash array

## Background

Fix the launch in dev.sh using a bash array. Files: dev.sh (replace `UVICORN_OPTS="$UVICORN_OPTS --reload"` string logic with `UVICORN_OPTS+=(--reload)` and change line 97 to `uvicorn app.main:app "${UVICORN_OPTS[@]}" &`). Verify: bash -n dev.sh — expect: syntax OK, exit 0.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KYZ9XNVTJE0XRHZ9F0Z4RFQX during the schema-4 cutover. -->
