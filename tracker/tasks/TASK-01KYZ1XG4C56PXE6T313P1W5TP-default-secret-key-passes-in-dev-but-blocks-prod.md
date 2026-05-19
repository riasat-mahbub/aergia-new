---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KYZ1XG4C56PXE6T313P1W5TP
TYPE: task
STATUS: DONE
SUMMARY: 'Default ''change-me-in-production'' raises RuntimeError in production mode'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- security
- config
- intentional
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:18:34.252608+00:00'
UPDATED_AT: '2026-08-01T16:18:34.252608+00:00'
---

# Default SECRET_KEY passes in dev but blocks prod

## Background

Default 'change-me-in-production' raises RuntimeError in production mode

The default `SECRET_KEY=change-me-in-production` in `.env.example` passes
through in development mode but raises a `RuntimeError` in production mode.
This is an intentional safety check — documented in AGENTS.md and DEPLOY.md.
The deployment guide instructs to generate a real key with
`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.

*Migrated from SCHEMA 2 entry 002-change-me-in-production.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation

Closed by design. Not a bug — intentional safety mechanism.

## Verification


## Follow-up
