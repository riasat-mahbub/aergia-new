---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3CXRDFQHFFDFBZZNSV16Q5D
TYPE: bug
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: Medium
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01M3CXQ5X9NHAKB6ZV91EVP35A
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
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-25T18:38:02.743164+00:00'
UPDATED_AT: '2026-09-25T18:38:02.743164+00:00'
---

# BUG-01M3CXQ5X9NHAKB6ZV91EVP35A

## Background

Extractor v9, five fixture references updated; focused extraction 44 passed; exact replay excludes all four Scotiabank employer-copy spans and retains adjacent qualification; broad scanner/tailoring 229 passed, 1 pre-existing bundle test deselected; escalated smoke gate passed including live gateway/SSR/CSP/auth. Awaiting extraction-agent paraphrase quality check.

## Investigation

The four employer-facing statements were:

- “We hire you for your talent — not just a job — so you can grow with us.”
- “Access to thousands of online and in-person courses so you can hone your current skills, or learn new ones.”
- “Candidates must apply directly online to be considered for this role.”
- “We thank all applicants for their interest in a career at Scotiabank; however, only those candidates who are selected for an interview will be contacted.”

The original posting and scan fixture were unavailable, so original heading
context could not be verified. Direct QA replay used plausible headings and
synthetic candidate_requirement spans.


## Decision

Exclude these employer benefit/application statements from candidate
requirements while retaining adjacent genuine qualifications. This is a
separate linked bug found after the completed employer-copy fix.


## Implementation

Extractor v9 extends employer-copy screening and updates five fixture references.


## Verification

Focused extraction: 44 passed. Direct replay excluded all four spans while
retaining “Experience building scalable engineering tools.” Broad
scanner/tailoring suite: 229 passed, 1 deselected for the pre-existing bundle
assertion. Escalated `./dev.sh --smoke` passed including live TanStack Start / 
FastAPI gateway, SSR, CSP, and auth. Awaiting extraction-agent paraphrase
quality check before closure.


## Follow-up
