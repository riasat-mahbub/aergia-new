---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3T1XCBYDC9FH6PG3N6XGD3S
TYPE: bug
STATUS: PROPOSED
PRIORITY: Medium
SEVERITY: Medium
EFFORT: null
OWNER: null
CONFIDENCE: High
TAGS:
- tailoring
- audit
- documentation
RELATIONS:
  depends_on:
  - TASK-01M3T1XBAA6W4NC1ZB1YY13W81
AFFECTS:
  files:
  - docs/matching-and-tailoring.md
  - api/alembic/versions/v0w1x2y3_full_history_tailoring_v9.py
  - api/app/services/library.py
  - docs/tailoring-audit-2026-09-30.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-30T21:00:47.358339+00:00'
UPDATED_AT: '2026-09-30T21:00:47.358339+00:00'
---

# Matching and tailoring documentation describes removed candidate indexing

## Background

Audit T12: docs/matching-and-tailoring.md describes current persistent indexing and workers although migration v0w1x2y3 drops those tables and protocol v9 removed retrieval. See docs/tailoring-audit-2026-09-30.md.

## Investigation

See findings and recommendations in the [audit report](../../docs/tailoring-audit-2026-09-30.md).

## Decision


## Implementation


## Verification

Compared the current documentation against protocol-v9 code and migration: index/state/semantic tables are dropped, while the documentation describes their ongoing updates and workers.

## Follow-up

Implement the report's recommendation and add permanent regression coverage.
No application fixes were made during the audit.
