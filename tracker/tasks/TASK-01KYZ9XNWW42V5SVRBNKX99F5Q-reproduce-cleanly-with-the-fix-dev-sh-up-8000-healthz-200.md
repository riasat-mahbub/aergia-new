---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KYZ9XNWW42V5SVRBNKX99F5Q
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
CREATED_AT: '2026-08-01T18:38:28.764661+00:00'
UPDATED_AT: '2026-08-01T18:38:28.764661+00:00'
---

# Reproduce cleanly with the fix (dev.sh up, :8000 healthz 200)

## Background

Reproduce cleanly with the fix. Files: dev.sh. Verify: kill stale node/vite+uvicorn, then ./dev.sh in background → ss -tlnp | grep :8000 then curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/healthz — expect: listener on :8000 present, curl returns 200.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
