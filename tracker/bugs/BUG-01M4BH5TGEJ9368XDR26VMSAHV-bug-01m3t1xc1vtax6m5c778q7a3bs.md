---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M4BH5TGEJ9368XDR26VMSAHV
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: High
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01M3T1XC1VTAX6M5C778Q7A3BS
AFFECTS: null
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-10-07T15:54:37.966240+00:00'
UPDATED_AT: '2026-10-07T15:54:37.966240+00:00'
---

# BUG-01M3T1XC1VTAX6M5C778Q7A3BS

## Background

Helper reads synthetic codes without echo in real PTY and pipe tests, restores terminal state, binds URL/exchange/context session identity, and treats reservation/preview/submit 401/403/410 as terminal. Server verifies URL session before code consumption. All Node files and backend release gates pass.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
