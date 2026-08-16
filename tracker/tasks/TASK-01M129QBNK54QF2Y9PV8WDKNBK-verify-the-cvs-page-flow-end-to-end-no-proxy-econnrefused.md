---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNBK
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
CREATED_AT: '2026-08-01T18:38:28.732980+00:00'
UPDATED_AT: '2026-08-01T18:38:28.732980+00:00'
---

# Verify the CVs page flow end-to-end (no proxy ECONNREFUSED)

## Background

Verify the CVs page flow end-to-end. Files: web/src (no change). Verify: with dev.sh up, curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/cvs and (browser) navigate to http://localhost:5173 → sign in → CVs page — expect: no vite proxy ECONNREFUSED; /api/v1/cvs returns 401 (unauthenticated) rather than the proxy 500/refused.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KYZ9XNVW9ZAQV7632ATNGQGQ during the schema-4 cutover. -->
