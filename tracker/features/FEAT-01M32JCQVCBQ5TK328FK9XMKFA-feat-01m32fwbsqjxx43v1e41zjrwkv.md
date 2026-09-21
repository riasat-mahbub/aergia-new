---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M32JCQVCBQ5TK328FK9XMKFA
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
  - FEAT-01M32FWBSQJXX43V1E41ZJRWKV
AFFECTS:
  files:
  - api/app/commands/scanner_backfill.py
  - api/app/scanner/extraction.py
  - api/app/scanner/matching.py
  - api/app/scanner/requirements.py
  - api/app/scanner/results.py
  - api/app/scanner/scoring.py
  - api/app/scanner/service.py
  - api/tests/test_scanner_backfill.py
  - api/tests/test_scanner_matching.py
  - api/tests/test_scanner_scoring.py
  - api/tests/test_scanner_application_api.py
  - api/alembic/env.py
  - api/tests/conftest.py
  - api/pyproject.toml
  - docs/plans/2026-09-21-scanner-shadow-migration-policy.md
  - web/src/features/applications/components/detail/ApplicationScannerPanel.tsx
  - web/src/features/applications/types/index.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-21T18:07:01.484755+00:00'
UPDATED_AT: '2026-09-21T18:07:01.484755+00:00'
---

# FEAT-01M32FWBSQJXX43V1E41ZJRWKV

## Background

Shadow migration run: initial dry run found 10 AttributeErrors; traced to constraint evidence with no concept hit in matching.py, fixed it, bumped matcher to requirement-match-v4, and added a regression test. Added --limit because --batch-size only controls database page size. Post-fix dry run: 28 scanned, 0 failed, 0 unscannable. Persisted AlayaCare canary, then bounded 10-row batch, then only-missing remainder: 1 + 10 + 17 scanned, 11 skipped, 0 failed, 0 unscannable. Database now has 28/28 current scanner-v1 results; all use matcher-v4. Legacy fields remain populated and tailoring/legacy relevance remain active. PDF recovery is unavailable for all 28 because the local Playwright driver is unavailable. AlayaCare manual review: Job Fit 52.3%, classified 87.5%, evidence-evaluable 100%, lexical visibility 35.2%; modern-practices expression has an extra not-evidenced umbrella child alongside AI partial, CI/CD and containerization supported, monitoring not evidenced. Reports saved under /tmp/aergia-scanner-backfill-*20260921.json. Follow up on umbrella component extraction, classification confidence gating, PDF renderer version provenance, and Playwright availability before authoritative cutover.

## Investigation

The first real dry run completed over 28 applications but reported 10
`AttributeError` failures. A single-app reproduction traced them to evidence
created from structured constraints without a concept hit; confidence
calculation dereferenced the absent concept match. The `--batch-size` option
was only limiting each database page, so the proposed 10-row canary would
otherwise have traversed the full database. The local Playwright driver is
unavailable, but PDF rendering failures are caught and reported as PDF
analysis unavailable.

## Decision

Guard the concept-confidence calculation and bump the matcher version so old
scanner results are no longer considered current. Keep `--batch-size` as the
database page size and add `--limit` as the total row cap for bounded canaries.
Proceed with shadow persistence after the post-fix dry run; keep legacy
relevance and tailoring consumers active.

## Implementation

Added a constraint-only evidence regression, updated matcher version to
`requirement-match-v4`, and added a database-page-aware total `--limit` with
coverage for multi-page selection. Ran the AlayaCare application first, then a
10-row canary, then `--only-missing` over the remainder. The backfill writes
scanner results while leaving legacy fields and tailoring snapshots alone.

## Verification

The focused matching/backfill suite passed: 23 tests. Ruff passed for the
changed scanner, command, and test files. The first dry run had 18 scanned and
10 failed; after the fix, dry run reported 28 scanned, zero failed, zero
unscannable. Persisted migration reports: AlayaCare 1 scanned; canary 10
scanned; remainder 17 scanned and 11 skipped; both real runs had zero failed
and zero unscannable. A database audit found 28/28 current results, all at
matcher-v4. PDF recovery is unavailable for all 28 because the Playwright
driver could not start. Tracker rebuild and validation completed with zero
errors and four existing fork warnings.

JSON reports are in `/tmp/aergia-scanner-backfill-dry-run-20260921.json`,
`/tmp/aergia-scanner-backfill-dry-run-post-fix-20260921.json`,
`/tmp/aergia-scanner-backfill-alayacare-first-persist-20260921.json`,
`/tmp/aergia-scanner-backfill-canary-10-20260921.json`, and
`/tmp/aergia-scanner-backfill-only-missing-25-20260921.json`.

## Follow-up

Review the extra `modern development practices` mandatory child in the
AlayaCare expression. Make score availability consider classification
coverage before authoritative cutover, add renderer-version provenance for
PDF freshness, and restore Playwright availability to enable PDF recovery.
Review the full shadow corpus before migrating application or tailoring
consumers and stopping legacy writes.
