---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KYZ9XNVP18V0S9J270W2PBCF
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
CREATED_AT: '2026-08-01T18:38:28.726747+00:00'
UPDATED_AT: '2026-08-01T18:38:28.726747+00:00'
---

# Add a regression test for the dev.sh uvicorn invocation

## Background

Add a regression test for the dev.sh uvicorn invocation. Files: dev.sh (test referenced in a new api/tests/test_devscript.py asserting the launcher doesn't pass a quoted multi-token string). Verify: cd api && source .venv/bin/activate && pytest tests/test_devscript.py -k shell — expect: test documents the quoted-vs-array contract and passes against the fixed script.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
