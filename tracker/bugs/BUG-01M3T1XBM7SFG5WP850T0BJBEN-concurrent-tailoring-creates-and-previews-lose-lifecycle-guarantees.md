---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3T1XBM7SFG5WP850T0BJBEN
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
  - api/app/services/tailoring.py
  - api/app/models/tailoring_session.py
  - docs/tailoring-audit-2026-09-30.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-30T21:00:46.599241+00:00'
UPDATED_AT: '2026-09-30T21:00:46.599241+00:00'
---

# Concurrent tailoring creates and previews lose lifecycle guarantees

## Background

Audit T04 T05: simultaneous creates return two active sessions and simultaneous successful previews persist only one evaluation. Reproduced using barriers in isolated API requests; see docs/tailoring-audit-2026-09-30.md.

## Investigation

See findings and recommendations in the [audit report](../../docs/tailoring-audit-2026-09-30.md).

## Decision


## Implementation


## Verification

Two preview requests synchronized at rendering both returned 200, but only one evaluation persisted. Two creation requests synchronized after the active-session query both returned 201 and left two created sessions.

## Follow-up

Implement the report's recommendation and add permanent regression coverage.
No application fixes were made during the audit.
