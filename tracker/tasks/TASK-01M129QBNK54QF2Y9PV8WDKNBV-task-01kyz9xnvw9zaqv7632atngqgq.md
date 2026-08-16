---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNBV
TYPE: task
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01M129QBNK54QF2Y9PV8WDKNBK
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T18:42:01.371962+00:00'
UPDATED_AT: '2026-08-01T18:42:01.371962+00:00'
---

# TASK-01KYZ9XNVW9ZAQV7632ATNGQGQ

## Background

With dev.sh up, /api/v1/cvs returns 401 (unauthenticated) directly and via vite proxy (no 500/ECONNREFUSED). Register->201, login->token, authed list CVs->200, create CV (title field)->201, templates->200. Full CVs data path works through localhost:5173 proxy. (Browser tool blocked localhost, verified via the same API the CVs page calls.)

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KYZA45GV35C7DRRZ6F737E4X during the schema-4 cutover. -->
