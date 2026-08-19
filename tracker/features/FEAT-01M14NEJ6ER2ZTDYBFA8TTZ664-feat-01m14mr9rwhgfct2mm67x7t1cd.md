---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M14NEJ6ER2ZTDYBFA8TTZ664
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M14MR9RWHGFCT2MM67X7T1CD
AFFECTS: null
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-28T17:07:32.174108+00:00'
UPDATED_AT: '2026-08-28T17:07:32.174108+00:00'
---

# FEAT-01M14MR9RWHGFCT2MM67X7T1CD

## Background

Step 5 complete: removed the current-password UI and all password-change state/validation, deleted the frontend auth-store method, removed the API route/request schema/service method, and updated regression tests to assert the endpoint is absent. Frontend 315 tests/build/codegen and Ruff pass; backend pytest was not runnable because the api/.venv aiosqlite connection hangs even against fresh temporary SQLite files.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
