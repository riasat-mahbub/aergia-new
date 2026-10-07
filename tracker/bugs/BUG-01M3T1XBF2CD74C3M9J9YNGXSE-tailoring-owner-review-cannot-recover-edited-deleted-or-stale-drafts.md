---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3T1XBF2CD74C3M9J9YNGXSE
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
  - api/app/services/cv.py
  - api/app/db/session.py
  - web/src/features/applications/components/detail/ApplicationCvPanel.tsx
  - docs/tailoring-audit-2026-09-30.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-30T21:00:46.434787+00:00'
UPDATED_AT: '2026-09-30T21:00:46.434787+00:00'
---

# Tailoring owner review cannot recover edited deleted or stale drafts

## Background

Audit T01 T02 T09: ordinary edits make acceptance impossible, ordinary deletion strands draft_ready sessions, and stale acceptance rolls back its status transition. Reproduced through isolated API requests; see docs/tailoring-audit-2026-09-30.md.

## Investigation

See findings and recommendations in the [audit report](../../docs/tailoring-audit-2026-09-30.md).

## Decision


## Implementation


## Verification

Isolated API reproductions confirmed: a title edit returns 200 but acceptance returns 409; deleted drafts cannot be rejected or replaced; stale acceptance returns 409 while persisted status remains draft_ready. An unchanged protocol-v9 draft still accepts successfully.

## Follow-up

Implement the report's recommendation and add permanent regression coverage.
No application fixes were made during the audit.
