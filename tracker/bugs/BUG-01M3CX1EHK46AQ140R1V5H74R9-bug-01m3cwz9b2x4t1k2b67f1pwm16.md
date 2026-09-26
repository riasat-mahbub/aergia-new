---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3CX1EHK46AQ140R1V5H74R9
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
  - BUG-01M3CWZ9B2X4T1K2B67F1PWM16
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
CREATED_AT: '2026-09-25T18:25:30.163266+00:00'
UPDATED_AT: '2026-09-25T18:25:30.163266+00:00'
---

# BUG-01M3CWZ9B2X4T1K2B67F1PWM16

## Background

Broad scanner/tailoring rerun: 228 passed, 1 failed. The sole failure is pre-existing bundle-content expectation (HEAD adds natural-writing.md); version-related failures are cleared. Full pytest/smoke checks are still running.

## Investigation

Section-aware candidate requirement extraction and independent scoring gates
address the employer-copy false positives. The exact QA replay excluded all six
examples while retaining two genuine qualifications. Extractor v8 and scorer
v4 version updates cleared version-related failures.


## Decision

Employer-facing instructions, legal/disclaimer text, accommodation notices,
and benefits must not become missing CV evidence or reduce Job Fit. Candidate
requirements remain eligible when mixed with surrounding employer context.


## Implementation

Implemented through scanner extraction/scoring and report interpretation
changes. Detailed behavior and versioning are recorded in the superseded
IN_PROGRESS entry.


## Verification

Focused extraction: 43 passed. Focused scoring: 21 passed before an additional
legacy-purpose gate. Frontend focused test, typecheck, lint, architecture and
codegen checks passed. Broad scanner/tailoring rerun: 228 passed, 1 failed; the
sole failure is pre-existing `test_tailoring_skill_bundle_contains_only_the_installable_skill_and_helper`,
because HEAD bundles `natural-writing.md` while the test expects two files.
Full pytest and smoke checks are still running.


## Follow-up
