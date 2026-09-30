---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3T1XBRS0N6S8X5CARQW19MB
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
  - api/app/services/tailoring_evaluation.py
  - api/app/http_schemas/tailoring_evaluation.py
  - docs/tailoring-audit-2026-09-30.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-30T21:00:46.745555+00:00'
UPDATED_AT: '2026-09-30T21:00:46.745555+00:00'
---

# Tailoring evaluation rejects keyword visibility variant transitions

## Background

Audit T06: exact to variant transitions produce changed_needs_review, which is invalid in TailoringPassChange and raises ValidationError. A valid revision can fail preview evaluation; see docs/tailoring-audit-2026-09-30.md.

## Investigation

See findings and recommendations in the [audit report](../../docs/tailoring-audit-2026-09-30.md).

## Decision


## Implementation


## Verification

A pure evaluator reproduction with previous exact visibility and current variant visibility raised Pydantic ValidationError for TailoringPassChange.classification.

## Follow-up

Implement the report's recommendation and add permanent regression coverage.
No application fixes were made during the audit.
