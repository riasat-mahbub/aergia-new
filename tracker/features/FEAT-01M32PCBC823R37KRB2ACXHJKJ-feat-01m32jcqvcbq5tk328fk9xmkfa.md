---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M32PCBC823R37KRB2ACXHJKJ
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
  - FEAT-01M32JCQVCBQ5TK328FK9XMKFA
AFFECTS:
  files:
  - api/README.md
  - api/alembic/versions/q2r3s4t5_add_scanner_rescan_state.py
  - api/app/commands/scanner_audit.py
  - api/app/commands/scanner_backfill.py
  - api/app/commands/scanner_pdf_smoke.py
  - api/app/http_schemas/application.py
  - api/app/models/application.py
  - api/app/routes/applications.py
  - api/app/scanner/audit.py
  - api/app/scanner/extraction.py
  - api/app/scanner/freshness.py
  - api/app/scanner/results.py
  - api/app/scanner/scoring.py
  - api/app/scanner/service.py
  - api/app/services/application.py
  - api/app/services/cv.py
  - api/app/services/renderer/_pdf_runtime.py
  - api/pyproject.toml
  - api/tests/fixtures/scanner/audit/shadow_results.json
  - api/tests/test_assets.py
  - api/tests/test_pdf_runtime.py
  - api/tests/test_profile.py
  - api/tests/test_scanner_application_api.py
  - api/tests/test_scanner_audit.py
  - api/tests/test_scanner_backfill.py
  - api/tests/test_scanner_extraction.py
  - api/tests/test_scanner_independent_analyses.py
  - api/tests/test_scanner_matching.py
  - api/tests/test_scanner_scoring.py
  - api/tests/test_tailoring.py
  - api/tests/test_templates.py
  - web/src/features/applications/components/detail/ApplicationScannerPanel.tsx
  - web/src/features/applications/types/index.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-21T19:16:43.016297+00:00'
UPDATED_AT: '2026-09-21T19:16:43.016297+00:00'
---

# FEAT-01M32JCQVCBQ5TK328FK9XMKFA

## Background

Follow-up completed: including-list umbrella extraction now produces only atomic list children; extractor is gliner2.5-structured-v6. Added scanner-audit and freshness reason reporting, low-classification caution, and application scanner lifecycle status. Forced refreshed all 28 shadow results (0 failed, 0 unscannable); audit found 28 current results. PDF smoke passes with Chromium access; the ordinary managed process sandbox blocks Chromium launch with Operation not permitted. Full API suite: 620 passed, 1 skipped. Updated stale assertions and made the Playwright singleton reset handles across closed event loops. Legacy relevance and tailoring remain unchanged.

## Investigation

The scanner follow-up started from a 28-application shadow run. It showed an
extra umbrella component in the AlayaCare `including` list, no audit command,
and no user-visible stale/needs-rescan state. PDF recovery was unavailable in
the earlier scan results. The full API suite also had stale expectations and a
Playwright lifecycle failure when run after other tests.

## Decision

Keep the scanner in shadow mode and leave legacy relevance and tailoring
consumers active. Preserve the score formula. Add diagnostic/freshness
reporting, mark low classification coverage as a caution, and make the
Playwright singleton safe across sequential event loops.

## Implementation

Added a general rule that removes an `including` umbrella from mandatory
siblings while preserving preceding independent components. Bumped the
extractor identity to `gliner2.5-structured-v6`. Added `scanner-audit`,
freshness reasons, a low-classification warning, and current/stale/not-scanned/
needs-rescan application status. Added a PDF runtime smoke command and a
Playwright loop-owner guard. Refreshed stale API tests without changing
tailoring or legacy relevance behavior.

## Verification

Forced dry-run and persisted backfill each processed 28 applications with zero
failures or unscannable rows. The final audit reported 28 current results and
zero stale/missing results. AlayaCare now has exactly four modern-practices
components: AI-assisted development partial, CI/CD supported, containerization
supported, monitoring not evidenced; the umbrella is absent. Job Fit is
52.7%, classified coverage 87.5%. The Chromium launch, Aergia render, and
pdfplumber smoke stages pass when run with browser process access; the normal
managed sandbox blocks Chromium with `Operation not permitted`. Its 28 current
PDF analyses are still marked fail on document recovery checks, so this does
not imply those PDFs pass. Full API suite: 620 passed, 1 skipped. Focused stale
contract/runtime group: 9 passed. Ruff and tracker validation passed.

## Follow-up

Keep shadow analysis active while collecting and reviewing a broader
development/held-out corpus. Calibrate acceptance thresholds before making
scanner results authoritative. Tailoring migration and legacy relevance
retirement remain explicitly out of scope until validation passes.
