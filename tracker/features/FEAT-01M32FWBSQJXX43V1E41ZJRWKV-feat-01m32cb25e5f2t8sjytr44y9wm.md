---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M32FWBSQJXX43V1E41ZJRWKV
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M32CB25E5F2T8SJYTR44Y9WM
AFFECTS:
  files:
  - api/alembic/env.py
  - api/app/commands/__init__.py
  - api/app/commands/scanner_backfill.py
  - api/app/scanner/extraction.py
  - api/app/scanner/requirements.py
  - api/app/scanner/results.py
  - api/app/scanner/scoring.py
  - api/app/scanner/service.py
  - api/pyproject.toml
  - api/tests/conftest.py
  - api/tests/test_scanner_application_api.py
  - api/tests/test_scanner_backfill.py
  - api/tests/test_scanner_contracts.py
  - api/tests/test_scanner_extraction.py
  - api/tests/test_scanner_independent_analyses.py
  - api/tests/test_scanner_scoring.py
  - docs/plans/2026-09-21-scanner-shadow-migration-policy.md
  - web/src/features/applications/components/detail/ApplicationScannerPanel.tsx
  - web/src/features/applications/types/index.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-21T17:23:07.703142+00:00'
UPDATED_AT: '2026-09-21T17:23:07.703142+00:00'
---

# FEAT-01M32CB25E5F2T8SJYTR44Y9WM

## Background

Fixed score coverage metadata and requirement/component status units, capped example support thresholds, stabilized Linux pytest/Alembic SQLite setup with uvloop, added a DB-backed scanner lifecycle regression, documented frozen legacy history policy, and added version-aware idempotent scanner-backfill. Full suite now completes: 603 passed, 1 skipped, 6 unrelated failures; focused scanner/API/backfill tests pass. Legacy relevance and tailoring consumers remain active during shadow migration.

## Investigation

The semantic score had one denominator for both requirement classification and
CV evidence evaluability. Headline status counts were top-level requirement
counts, even when a child component was unverifiable. Example-list extraction
hard-coded a two-example threshold, including one-item lists.

The default Python 3.14 selector loop stalled on aiosqlite's worker-thread
completion during SQLite/Alembic setup. Uvloop completed the same connection
and migration, and is already supplied by the Linux `uvicorn[standard]`
runtime dependency.

Application scanner persistence and CV/JD invalidation were already wired.
The missing piece was a repeatable normal pytest bootstrap and a shadow
backfill that preserves the active legacy writes and persisted snapshots.


## Decision

Report classified JD requirement weight and CV-evaluable classified weight as
separate fractions. Keep legacy scanner-v1 fields readable, but make new
requirement-level counts explicit and report unverifiable component counts
separately.

Use uvloop for Linux tests and Alembic migrations. Generate `scanner_result`
from current JD/CV inputs only. Do not translate existing legacy relevance,
quality, keyword, algorithm-version, or tailoring snapshot data. Continue
legacy writes during shadow migration; freeze those fields only at consumer
cutover.


## Implementation

Added a model-level cap and extraction-time cap for example support thresholds;
versioned the changed score/extractor behavior; exposed classification/evidence
coverage and requirement/component counts in API and UI; stabilized Alembic and
pytest database initialization; added full linked-CV lifecycle coverage; wrote
the legacy-history policy; and added a console `scanner-backfill` with
dry-run, keyset batching, application targeting, force/only-missing behavior,
input/version freshness checks, per-application commits, and failure isolation.

Atomic commits: `9ae74eb`, `000a2eb`, `0bf0439`, `608a8de`, `0bcfeee`, `67df1de`.


## Verification

Passed: 79 isolated scanner tests; 4 normal DB-backed scanner API/backfill
tests; Ruff; frontend typecheck, lint (9 existing warnings), and architecture
checks; fresh-database Alembic upgrade without a test-only environment flag;
and `scanner-backfill --help` through the installed console entry point.

The full backend suite now completes rather than hanging: 603 passed, 1
skipped, 6 failed. The failures are outside the scanner changes: asset route
redirect status, profile normalization expectations, unavailable Playwright
driver, tailoring bundle text expectation, and two stale template tests.


## Follow-up

Keep the scanner in shadow mode while the annotated corpus is built and
validated. Compare backfilled results, then migrate application/tailoring
consumers and retire legacy relevance only after the validation gates pass.
