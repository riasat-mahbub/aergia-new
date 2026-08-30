---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M18B0XM83MG2JG64D735FAAN
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
CREATED_AT: '2026-08-30T03:22:17.096763+00:00'
UPDATED_AT: '2026-08-30T03:22:17.096763+00:00'
---

# auth-session-rate-limit-response

## Background

The /api/v1/auth/session endpoint is decorated with SlowAPI but does not declare a Starlette Response parameter. When the limiter is enabled and the endpoint returns a JSON dict, SlowAPI cannot inject rate-limit headers and raises an exception, producing HTTP 500 after successful login. Fix is isolated from the shared checkout.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
