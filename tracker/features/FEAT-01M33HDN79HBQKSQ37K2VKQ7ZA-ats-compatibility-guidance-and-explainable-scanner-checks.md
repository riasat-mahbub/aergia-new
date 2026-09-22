---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M33HDN79HBQKSQ37K2VKQ7ZA
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  depends_on:
    - FEAT-01M32JCQVCBQ5TK328FK9XMKFA
AFFECTS:
  files:
    - api/app/scanner/ats_results.py
    - api/app/scanner/ats_guidance.py
    - api/app/scanner/results.py
    - api/app/scanner/service.py
    - api/app/scanner/freshness.py
    - api/app/scanner/audit.py
    - api/app/scanner/pdf_recovery.py
    - api/app/commands/scanner_backfill.py
    - api/app/commands/scanner_audit.py
    - api/tests/test_scanner_ats_guidance.py
    - api/tests/test_scanner_pdf_recovery.py
    - web/src/features/applications/domain/scannerReport.ts
    - web/src/features/applications/domain/scannerReport.test.ts
    - web/src/features/applications/components/ScannerAnalysisDrawer.tsx
    - web/src/features/applications/types/index.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-22T03:09:17.417761+00:00'
UPDATED_AT: '2026-09-22T03:09:17.417761+00:00'
---

# ATS compatibility guidance and explainable scanner checks

## Background

Add deterministic ATS compatibility analyses and guidance for all supported ATS profiles, plus human-readable scanner and PDF findings in the application UI. Keep existing Job Fit, lexical, quality, and PDF recovery semantics unchanged.

## Investigation

The scanner already had authoritative semantic, lexical, presentation, and
PDF recovery branches. The missing layer was interpretation: conventional
headings, rendered date formats, explicit acronym pairs, structured entry
fields, and a common explanation of parser facts. Platform-specific claims
were reviewed conservatively; no unsupported vendor behavior was added.


## Decision

Keep one deterministic ATS guidance contract (`ats-guidance-v1`) on top of
existing scanner facts. Generate all fourteen supported platform entries on
every scan, with shared findings deduplicated in the common layer. Leave the
source registry empty until a platform claim has a defensible source. Keep
human-readable explanation and evidence shaping in the frontend view model.


## Implementation

Added four generic analyses: heading convention, rendered date compatibility,
acronym/full-form coverage, and structured entry completeness. Added common
rule and source contracts, fourteen-platform registry validation, semantic-safe
keyword guidance, and ATS findings in persisted `ScanResult` objects. PDF link
identities now use human-readable labels. The application analysis UI explains
PDF checks, common ATS findings, and compact per-platform guidance without
exposing raw renderer IDs or expression trees. A small date-range regression
fix accepts full rendered month-to-month ranges as conventional.


## Verification

Focused ATS/PDF/scanner suite: 84 passed before the final date regression;
ATS guidance suite: 8 passed after it. Full approved-runtime API suite:
664 passed, 1 skipped. Ruff passed. Frontend typecheck, architecture checks,
codegen check, and scanner report test passed; lint has nine existing hook
dependency warnings and no errors. The 28-application forced backfill ran
with 0 failures and 0 unscannable applications. Final audit: 28 current, 0
stale, 0 missing, all with `ats-guidance-v1` and all fourteen platform IDs.


## Follow-up

Add sourced platform-specific rules only after verifying vendor or independent
evidence. Keep ATS guidance separate from Job Fit, Term Visibility, Resume
Quality, and PDF recovery scores; no per-ATS score or universal ATS claim was
introduced.

## Correction update — 2026-09-22

Shared ATS advice is emitted once in `common_findings`. The fourteen platform
records are deliberately delta-only and currently contain no copied common
findings or unsourced tips. This keeps a general recommendation from being
mistaken for fourteen independent platform claims. Entry completeness now
handles renderer field aliases (including project `name`) through explicit
alias groups. Commit `a45cae1` added these changes and regression coverage.

The persisted corpus was force-rescanned after the correction: 28 scanned, 0
failed, and 0 unscannable. Audit reports 28 current, 0 stale, and 0 missing
results; all 28 have fourteen platform IDs and zero non-empty platform delta
lists. Focused ATS/scanner tests pass (139 tests); the full API suite passes
(668 passed, 1 skipped). Legacy relevance and tailoring remain unchanged.
