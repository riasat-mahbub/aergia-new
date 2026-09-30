---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3T1XBXRWSBCTZAHHXBF2GSZ
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
  - web/src/features/tailoring/hooks/useTailoringSession.ts
  - web/src/features/applications/pages/ApplicationDetailPage.tsx
  - docs/tailoring-audit-2026-09-30.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-30T21:00:46.904094+00:00'
UPDATED_AT: '2026-09-30T21:00:46.904094+00:00'
---

# Tailoring UI retains and acts on another application session

## Background

Audit T03: changing applicationId to an application with no latest session leaves the previous session in useTailoringSession; accept then targets that previous session. Reproduced with real React in Chromium and mocked API responses; see docs/tailoring-audit-2026-09-30.md.

## Investigation

See findings and recommendations in the [audit report](../../docs/tailoring-audit-2026-09-30.md).

## Decision


## Implementation


## Verification

The real React hook ran in Chromium with synthetic API responses. After switching from application A to B with no session, state still named session A and the acceptance callback targeted A.

## Follow-up

Implement the report's recommendation and add permanent regression coverage.
No application fixes were made during the audit.
