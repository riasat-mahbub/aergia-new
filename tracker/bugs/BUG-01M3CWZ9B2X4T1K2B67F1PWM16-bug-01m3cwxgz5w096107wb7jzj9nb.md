---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3CWZ9B2X4T1K2B67F1PWM16
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
  - BUG-01M3CWXGZ5W096107WB7JZJ9NB
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
CREATED_AT: '2026-09-25T18:24:19.298263+00:00'
UPDATED_AT: '2026-09-25T18:24:19.298263+00:00'
---

# BUG-01M3CWXGZ5W096107WB7JZJ9NB

## Background

Employer-directed application instructions, legal disclaimers, accommodation notices, and benefits could be extracted as candidate requirements and lower Job Fit or appear as missing CV evidence.

## Investigation

The earlier scanner hardening audit recorded unchanged Job Fit and classification
results and left semantic requirement filtering as a separate follow-up. The
reported examples are employer instructions, legal copy, accommodation text,
and benefits. They must not be treated as candidate evidence requirements or
penalize the Job Fit score. Genuine candidate qualifications in surrounding
sections must remain eligible.


## Decision

Classify requirement content using section context and candidate-facing
qualification semantics. Ensure scoring excludes employer-facing copy even if
an importance label is present, and keep the report's missing-requirement view
consistent with that classification. Bump scanner freshness/version metadata
as needed so previously stored analyses are regenerated.


## Implementation

Extractor v8 and scorer v4 implement the updated extraction and scoring gates.
Exact QA replay excludes all six employer-copy examples and retains two genuine
candidate qualifications. Integration verification is ongoing.


## Verification

Focused extraction tests: 43 passed. Focused scoring tests: 21 passed before an
additional legacy-purpose gate was added. Frontend focused report tests,
typecheck, lint, architecture checks, and codegen checks pass. Broad backend
suite is still running, with failures under investigation.


## Follow-up
