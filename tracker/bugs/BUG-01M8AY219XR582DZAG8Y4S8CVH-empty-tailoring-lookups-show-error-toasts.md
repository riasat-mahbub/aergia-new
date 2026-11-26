---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M8AY219XR582DZAG8Y4S8CVH
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: Medium
EFFORT: S
OWNER: null
CONFIDENCE: High
TAGS:
- frontend
- tailoring
- error-states
RELATIONS:
  related:
  - TASK-01M3T3ZA8J0528X078077XQK22
  - TASK-01M3T3ZADCFTVD5Z2FJ8BNWPTE
AFFECTS:
  files:
  - web/src/features/tailoring/api/tailoring.ts
  - web/src/features/tailoring/hooks/useTailoringSession.ts
  - web/src/features/builder/hooks/useBuilderApplicationContext.ts
  - web/src/shared/api/client.ts
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T03:23:18.205452+00:00'
UPDATED_AT: '2026-11-26T03:51:32.984783+00:00'
---

# Expected empty tailoring lookups show error toasts

## Background

The application detail checks for the latest tailoring session on load. The builder checks for tailoring-draft context even when it is opening an ordinary CV. A missing optional resource is expected in both flows.

## Investigation

1. Open an existing application that has never had a tailoring session.
2. Open a regular saved CV from **My CVs**.

**Actual.** The application shows **Tailoring session not found**. The builder displays the CV and its preview while also showing **CV not found**. The shared Axios response interceptor emits the error toast before the workflow can handle the expected 404.

**Expected.** These two empty responses quietly resolve to the workflow’s normal view. Real missing CVs, unavailable pending drafts, and unexpected failures continue to produce their appropriate feedback.

## Verification

Chromium with the production client confirmed that the two initial 404s emit no toast. Linked scanner context still loads, a genuinely missing CV still reports its load error, and simulated 403 and 503 responses still report errors. The mounted tailoring session and builder suites passed conflict recovery and pending-draft scenarios.

Reproduced both toasts in Chromium on commit `78f71d2`. The application latest-session lookup returned 404. The regular CV successfully loaded and rendered its preview while the optional draft lookup emitted the toast.
