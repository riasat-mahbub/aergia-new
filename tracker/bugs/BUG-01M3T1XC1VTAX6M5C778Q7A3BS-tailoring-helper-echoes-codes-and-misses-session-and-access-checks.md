---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3T1XC1VTAX6M5C778Q7A3BS
TYPE: bug
STATUS: PROPOSED
PRIORITY: High
SEVERITY: High
EFFORT: null
OWNER: null
CONFIDENCE: High
TAGS:
- tailoring
- audit
RELATIONS:
  depends_on:
  - TASK-01M3T1XBAA6W4NC1ZB1YY13W81
AFFECTS:
  files:
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/tests/session.test.mjs
  - docs/tailoring-audit-2026-09-30.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-30T21:00:47.035903+00:00'
UPDATED_AT: '2026-09-30T21:00:47.035903+00:00'
---

# Tailoring helper echoes codes and misses session and access checks

## Background

Audit T07 T10 T11: readline echoes the one-time code even with terminal ECHO disabled; exchange and context IDs are not checked against the link; preview access failures stay repairable. Reproduced with synthetic data; see docs/tailoring-audit-2026-09-30.md.

## Investigation

See findings and recommendations in the [audit report](../../docs/tailoring-audit-2026-09-30.md).

## Decision


## Implementation


## Verification

A PTY with ECHO disabled still captured the complete synthetic code. Mock exchange/context IDs differing from the URL reached candidate authoring. Preview HTTP 401 allowed another RENDER request.

## Follow-up

Implement the report's recommendation and add permanent regression coverage.
No application fixes were made during the audit.
