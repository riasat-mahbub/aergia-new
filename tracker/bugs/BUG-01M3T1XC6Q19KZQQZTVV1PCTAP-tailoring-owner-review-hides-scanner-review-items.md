---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3T1XC6Q19KZQQZTVV1PCTAP
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
RELATIONS:
  depends_on:
  - TASK-01M3T1XBAA6W4NC1ZB1YY13W81
AFFECTS:
  files:
  - web/src/features/applications/components/detail/ApplicationCvPanel.tsx
  - web/src/features/tailoring/types/index.ts
  - api/app/services/tailoring_evaluation.py
  - docs/tailoring-audit-2026-09-30.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-30T21:00:47.191745+00:00'
UPDATED_AT: '2026-09-30T21:00:47.191745+00:00'
---

# Tailoring owner review hides scanner review items

## Background

Audit T08: ApplicationCvPanel never displays evaluation.review_items, hiding requirement conflicts and ATS warnings. The ordinary builder ignores application scanner context for unlinked drafts; see docs/tailoring-audit-2026-09-30.md.

## Investigation

See findings and recommendations in the [audit report](../../docs/tailoring-audit-2026-09-30.md).

## Decision


## Implementation


## Verification

Source tracing confirmed evaluation.review_items carries requirement conflicts and ATS warnings but has no render path in ApplicationCvPanel. The builder excludes scanner context for unlinked draft CVs.

## Follow-up

Implement the report's recommendation and add permanent regression coverage.
No application fixes were made during the audit.
