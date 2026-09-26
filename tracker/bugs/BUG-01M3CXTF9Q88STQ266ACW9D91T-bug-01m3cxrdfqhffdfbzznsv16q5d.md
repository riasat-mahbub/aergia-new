---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3CXTF9Q88STQ266ACW9D91T
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
  - BUG-01M3CXRDFQHFFDFBZZNSV16Q5D
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
CREATED_AT: '2026-09-25T18:39:10.135358+00:00'
UPDATED_AT: '2026-09-25T18:39:10.135358+00:00'
---

# BUG-01M3CXRDFQHFFDFBZZNSV16Q5D

## Background

Paraphrase quality audit found four false-positive gaps; fixed with regression coverage. Final extractor now v10, focused extraction 45 passed, and real experience with online application systems remains extracted. Integration is updating v9 fixture references and rerunning broad/smoke checks.

## Investigation

Paraphrase quality checking found four additional false-positive gaps, which
were fixed with regression coverage. The exact employer-facing source spans
under audit were:

- “We hire you for your talent — not just a job — so you can grow with us.”
- “Access to thousands of online and in-person courses so you can hone your current skills, or learn new ones.”
- “Candidates must apply directly online to be considered for this role.”
- “We thank all applicants for their interest in a career at Scotiabank; however, only those candidates who are selected for an interview will be contacted.”

The original posting and scan fixture were unavailable, so original heading
context could not be verified. Earlier replay used plausible headings and
synthetic candidate_requirement spans.


## Decision

Exclude employer benefits/application copy from requirements while keeping
genuine candidate qualifications, including real experience with online
application systems, eligible for extraction. This remains a separate follow-up
to the completed general employer-copy fix.


## Implementation

Extractor v10 addresses the paraphrase audit gaps; regression coverage was
added. Integration is updating the related extractor-version fixture refs.


## Verification

Focused extraction: 45 passed. The quality check confirmed real experience
with online application systems remains extracted. Earlier broad scanner /
tailoring suite passed 229 tests with one pre-existing bundle test deselected;
v10 broad and smoke reruns are in progress.


## Follow-up
