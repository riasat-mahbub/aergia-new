---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3CWXGZ5W096107WB7JZJ9NB
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
CREATED_AT: '2026-09-25T18:23:21.573530+00:00'
UPDATED_AT: '2026-09-25T18:23:21.573530+00:00'
---

# Employer posting copy counted as CV requirements

## Background

Employer-directed application instructions, legal disclaimers, accommodation notices, and benefits can be extracted as candidate requirements and lower Job Fit or appear as missing CV evidence.

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

Implementation is in progress; record exact code behavior after integration.


## Verification

Awaiting focused regression and integration test results.


## Follow-up
