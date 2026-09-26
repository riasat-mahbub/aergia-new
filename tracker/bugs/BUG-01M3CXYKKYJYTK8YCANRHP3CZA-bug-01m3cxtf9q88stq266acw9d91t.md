---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3CXYKKYJYTK8YCANRHP3CZA
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: Medium
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01M3CXTF9Q88STQ266ACW9D91T
  depends_on:
  - BUG-01M3CXFAPJGQEAFQ07T3X5FG3C
AFFECTS:
  files:
  - api/app/scanner/extraction.py
  - api/app/scanner/scoring.py
  - api/tests/test_scanner_application_api.py
  - api/tests/test_scanner_backfill.py
  - api/tests/test_scanner_extraction.py
  - api/tests/test_scanner_independent_analyses.py
  - api/tests/test_scanner_scoring.py
  - api/tests/test_tailoring.py
  - api/tests/test_tailoring_contracts.py
  - web/src/features/applications/domain/scannerReport.ts
  - web/src/features/applications/domain/scannerReport.test.ts
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-25T18:41:25.630688+00:00'
UPDATED_AT: '2026-09-25T18:41:25.630688+00:00'
---

# BUG-01M3CXTF9Q88STQ266ACW9D91T

## Background

Extractor v10 fixes four paraphrase-audit gaps with regression coverage. Focused extraction 45 passed; online-application-system experience remains extracted. Broad scanner/tailoring: 230 passed, 1 pre-existing bundle assertion failed; with it deselected 230 passed, 1 deselected. Escalated ./dev.sh --smoke passed including live gateway.

## Investigation

Four Scotiabank employer-facing benefit/application statements were originally
treated as candidate requirements. Paraphrase quality checking found four
additional false-positive gaps; regression coverage and extractor v10 address
them. The original posting and scan fixture were unavailable, so the source
heading context remains unverified.


## Decision

Exclude employer benefits and application-process copy while preserving real
candidate qualifications, including experience with online application
systems. This is a new follow-up linked to the completed general employer-copy
bug, not a reopening of that item.


## Implementation

Extractor v10 includes the additional employer-copy screening and regression
coverage. The related fixture references were updated for the extractor
version.


## Verification

Focused extraction: 45 passed. QA confirmed online-application-system
experience remains extracted. Broad scanner/tailoring: 230 passed with 1
failure in the pre-existing bundle-content assertion; rerunning with that
assertion deselected produced 230 passed, 1 deselected. Escalated
`./dev.sh --smoke` passed, including the live gateway.


## Follow-up
