---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M332V55C2YFT4DVJQFT9SCDT
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
  - FEAT-01M30GRJYZWECYHY30NCJJAX1R
AFFECTS:
  files:
  - api/alembic/versions/r3s4t5u6_add_tailoring_v4_context.py
  - api/app/http_schemas/tailoring.py
  - api/app/models/tailoring_session.py
  - api/app/routes/tailoring.py
  - api/app/scanner/service.py
  - api/app/services/tailoring.py
  - api/tests/test_tailoring.py
  - api/tests/test_tailoring_contracts.py
  - tailoring-skill/SKILL.md
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/references/context.schema.json
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - tailoring-skill/tests/session.test.mjs
  - web/src/features/applications/components/detail/ApplicationCvPanel.tsx
  - web/src/features/tailoring/hooks/useTailoringSession.ts
  - web/src/features/tailoring/types/index.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-21T22:54:31.085017+00:00'
UPDATED_AT: '2026-09-21T22:54:31.085017+00:00'
---

# FEAT-01M30GRJYZWECYHY30NCJJAX1R

## Background

Migrated new tailoring sessions to protocol v4 with a frozen scanner RequirementExtraction, scanner-backed source/preview/submit/accept results, candidate fingerprint verification, historical-result preservation, and scanner-native application review UI. Legacy relevance writes and tailoring snapshots remain active until separate post-validation cutover.

## Investigation

The pre-v4 service still built tailoring context from legacy JobRequirement
objects and evaluated preview/submission candidates with legacy relevance and
quality helpers. The browser review panel also displayed the legacy snapshot
from new tailoring results. A persisted draft could additionally appear stale
after submission because CV persistence removes null document fields that the
preview fingerprint retained.


## Decision

Protocol v4 freezes one scanner RequirementExtraction in a session-owned
context snapshot. Scanner evaluation is shared between source analysis,
preview, submit, and acceptance. New session payloads expose scanner results;
old result JSON remains inert history. Candidate fingerprints use renderer
inputs and acceptance verifies both the stored candidate binding and persisted
draft content. Legacy relevance remains active for consumers outside this
tailoring migration.


## Implementation

Added the v4 session/protocol migration, scanner evaluation from frozen
extractions, source-CV reuse/rescan, no-source-CV extraction, scanner-native
preview/submit/review contracts, acceptance compare-and-swap promotion, and
historical result tolerance. Canonicalized preview and persisted CV document
payloads. Updated the portable skill, critique inputs, protocol checks, and
the application tailoring review panel/types to use scanner Job Fit and render
warnings.


## Verification

Focused tailoring/scanner/API lifecycle suites: 53 passed in the final
verification run. Full API suite with browser process access: 634 passed, 1
skipped. Ruff passed. Portable skill tests: 3 passed. Frontend lint completed
with nine pre-existing hook warnings; typecheck, architecture checks, and
codegen checks passed. Elevated PDF smoke passed for Playwright, Chromium,
Aergia rendering, and pdfplumber recovery. Normal managed sandbox PDF launch
remains blocked by its process restriction.


## Follow-up

Keep legacy relevance writes and old tailoring snapshots until scanner
validation and a separate consumer-cutover task authorize stopping them.
Historical protocol-v2 result payloads remain readable but are not converted
to scanner-v1.

The v4 tailoring path now rejects sessions when the frozen scanner contract or
submitted scanner result is stale, and acceptance promotes only the scanner
result evaluated for the exact submitted candidate. Application-facing legacy
relevance remains outside this task and is still active for non-tailoring
consumers.
