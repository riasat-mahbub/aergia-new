---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M18B4D1WH6Z8B57G24NBG42Y
TYPE: bug
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: High
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS:
- auth
- rate-limit
- regression
RELATIONS: null
AFFECTS: null
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-30T03:24:11.196146+00:00'
UPDATED_AT: '2026-08-30T03:24:11.196146+00:00'
---

# auth-session-rate-limit-response

## Background

The /api/v1/auth/session endpoint is decorated with SlowAPI but does not declare a Starlette Response parameter. When the limiter is enabled and the endpoint returns a JSON mapping, SlowAPI cannot inject rate-limit headers and raises an exception, producing HTTP 500 after successful login.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
