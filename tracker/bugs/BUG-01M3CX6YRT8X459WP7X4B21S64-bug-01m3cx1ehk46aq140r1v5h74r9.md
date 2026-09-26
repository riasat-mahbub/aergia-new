---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3CX6YRT8X459WP7X4B21S64
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
  - BUG-01M3CX1EHK46AQ140R1V5H74R9
  depends_on:
  - BUG-01M339P61TKT5MPVHPYXMRHT1X
AFFECTS:
  files:
  - api/app/scanner/extraction.py
  - api/app/scanner/scoring.py
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
CREATED_AT: '2026-09-25T18:28:30.618275+00:00'
UPDATED_AT: '2026-09-25T18:28:30.618275+00:00'
---

# BUG-01M3CX1EHK46AQ140R1V5H74R9

## Background

Full backend pytest: 765 passed, 1 skipped, 4 failed. Two renderer assertions relate to an unrelated pre-existing html_document.py chip-style change; one Playwright driver closed in full-pipeline PDF test (isolated rerun pending); one pre-existing tailoring-skill bundle test mismatch. Awaiting smoke and isolated PDF rerun.

## Investigation

Section-aware candidate requirement extraction and independent scoring gates
address the employer-copy false positives. Exact QA replay excluded all six
examples while retaining two genuine qualifications. Extractor v8 and scorer
v4 cleared version-related failures.


## Decision

Employer-facing instructions, legal/disclaimer text, accommodation notices,
and benefits must not become missing CV evidence or reduce Job Fit. Candidate
requirements remain eligible when mixed with surrounding employer context.


## Implementation

Implemented through scanner extraction/scoring and report interpretation
changes. Prior chain revisions retain the detailed change and focused test
results.


## Verification

Focused extraction: 43 passed. Focused scoring: 21 passed before an additional
legacy-purpose gate. Frontend focused test, typecheck, lint, architecture and
codegen checks passed. Broad scanner/tailoring rerun: 228 passed, 1 failed due
to a pre-existing bundle-content expectation (`natural-writing.md` is included
by HEAD, while the test expects two files). Full backend pytest: 765 passed, 1
skipped, 4 failed. Two renderer assertions relate to an unrelated existing
`html_document.py` chip-style modification; one Playwright driver closed in the
full-pipeline PDF test (isolated rerun pending); the fourth is the same skill
bundle mismatch. Await smoke results and isolated PDF rerun before closure.


## Follow-up
