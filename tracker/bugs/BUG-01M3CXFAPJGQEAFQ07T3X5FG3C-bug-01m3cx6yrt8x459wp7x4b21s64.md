---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3CXFAPJGQEAFQ07T3X5FG3C
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
  - BUG-01M3CX6YRT8X459WP7X4B21S64
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
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-25T18:33:04.978127+00:00'
UPDATED_AT: '2026-09-25T18:33:04.978127+00:00'
---

# BUG-01M3CX6YRT8X459WP7X4B21S64

## Background

Employer-copy false positives fixed with section-aware extractor v8, scorer v4, candidate-facing report filtering, and version invalidation. Relevant scanner/tailoring suite: 228 passed, 1 deselected (pre-existing bundle expectation); escalated isolated PDF test passed; escalated ./dev.sh --smoke passed. Full sandboxed backend pytest: 765 passed, 1 skipped, 4 failures (two unrelated renderer styling assertions, one PDF Playwright sandbox failure cleared by isolated escalated pass, one pre-existing skill bundle expectation).

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
changes, with extractor v8 and scorer v4 version invalidation. Earlier chain
revisions retain the detailed engineering notes.


## Verification

Focused extraction: 43 passed. Focused scoring: 21 passed before the additional
legacy-purpose gate. Frontend focused test, typecheck, lint, architecture and
codegen checks passed. Relevant scanner/tailoring suite: 228 passed, 1
deselected for the pre-existing bundle expectation. Escalated isolated PDF test
passed (1), and escalated `./dev.sh --smoke` passed including live gateway,
SSR, CSP, and auth.

Full sandboxed backend pytest: 765 passed, 1 skipped, 4 failed. Two failures
are renderer assertions tied to a pre-existing unrelated
`html_document.py` chip-style change; the full-pipeline PDF failure was a
sandboxed Playwright driver closure and passed in the isolated escalated rerun;
the remaining failure is the pre-existing skill bundle mismatch (HEAD bundles
`natural-writing.md`, while the test expects two files).


## Follow-up
