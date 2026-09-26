---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3CXQ5X9NHAKB6ZV91EVP35A
TYPE: bug
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: Medium
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- scanner
- requirements
RELATIONS:
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
CREATED_AT: '2026-09-25T18:37:22.217235+00:00'
UPDATED_AT: '2026-09-25T18:37:22.217235+00:00'
---

# Scotiabank posting copy counted as candidate requirements

## Background

A Scotiabank job posting contains four employer-directed statements that extractor v8 treats as candidate requirements, producing false missing-CV signals or lowering Job Fit. Revisit candidate-facing qualification classification for these cases.

## Investigation

Scotiabank's posting included four employer-directed statements that were
explicitly tagged as `candidate_requirement` spans:

- “We hire you for your talent — not just a job — so you can grow with us.”
- “Access to thousands of online and in-person courses so you can hone your current skills, or learn new ones.”
- “Candidates must apply directly online to be considered for this role.”
- “We thank all applicants for their interest in a career at Scotiabank; however, only those candidates who are selected for an interview will be contacted.”

The source posting and original scan fixture were unavailable, so the original
heading context could not be verified. Regression QA replayed the exact spans
with plausible headings and synthetic candidate_requirement annotations.


## Decision

Exclude these four employer-facing benefit/application statements from
candidate requirement output while preserving adjacent genuine qualifications.
Keep this as a separate bug linked to the completed employer-copy fix: these
are additional examples found after that prior fix, not a reopening of its
completed scope.


## Implementation

Extractor v9 extends employer-copy screening. Five fixture references were
updated with the version change.


## Verification

Focused extraction suite: 44 passed. QA direct replay excluded all four
examples and retained the adjacent “Experience building scalable engineering
tools” qualification. Broad scanner/tailoring suite: 229 passed, 1 deselected
for the pre-existing bundle assertion. Smoke verification is still running.


## Follow-up
