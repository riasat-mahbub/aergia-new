---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M3A4R1NB3GW8GNJ6HGHQDHNB
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
- protocol-v8
- submission
RELATIONS:
  depends_on:
  - FEAT-01M38W5XGNVE9ZEW3S7EHTTYX9
  supersedes:
  - FEAT-01M3A4QBFQ66HY1GDNVZ4XA4NF
AFFECTS:
  files:
  - api/app/http_schemas/tailoring.py
  - api/app/http_schemas/tailoring_evaluation.py
  - api/app/models/tailoring_session.py
  - api/app/routes/tailoring.py
  - api/app/services/tailoring.py
  - api/app/services/tailoring_evaluation.py
  - api/alembic/versions/u9v0w1x2_tailoring_protocol_v8.py
  - api/tests/test_tailoring.py
  - api/tests/test_tailoring_contracts.py
  - api/tests/test_tailoring_evaluation.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - tailoring-skill/skills/aergia-tailor/scripts/validate-editorial-review.mjs
  - tailoring-skill/skills/aergia-tailor/references/context.schema.json
  - tailoring-skill/skills/aergia-tailor/references/editorial-review.schema.json
  - tailoring-skill/tests/editorial-review.test.mjs
  - tailoring-skill/tests/session.test.mjs
  - web/src/features/tailoring/api/tailoring.ts
  - web/src/features/tailoring/types/index.ts
  - web/src/features/applications/components/detail/ApplicationCvPanel.tsx
  - docs/matching-and-tailoring.md
  - scripts/smoke.sh
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-24T16:42:27.371215+00:00'
UPDATED_AT: '2026-09-24T16:42:27.371215+00:00'
---

# FEAT-01M3A4QBFQ66HY1GDNVZ4XA4NF

## Background

A preview evaluation ID plus candidate hash now binds the frozen candidate and editorial review through submission; findings remain advisory, and saved v4-v7 drafts stay reviewable.

## Investigation

Protocol v7 submission selected candidates through fallback/readiness behavior,
so the helper could not safely keep earlier reviewed candidates selectable.
Preview responses lacked unique evaluation identities, the server history did
not retain every selectable attempt, and the helper exited after recoverable
submit errors. Saved v4-v7 drafts also needed to remain reviewable after the
active evaluation schema changed.
## Decision

Use protocol v8 as a breaking contract. Every candidate preview receives an
opaque server-issued evaluation ID and server-computed candidate hash. The
agent explicitly selects a frozen reviewed attempt; the submit request and
editorial review bind to those values. Findings remain advisory. Keep the
five-preview resource limit, retryable capability loop, idempotent result
replay, and historical owner-review flow.
## Implementation

- Replaced readiness and pass metadata with risk findings and ordered
  previous-evaluation comparisons; raised evaluation and editorial review
  schemas to v2.
- Added a separate source-preview DTO, retained all candidate evaluation
  records, and bound submit validation to the chosen preview and review.
- Added replay digests, selected evaluation metadata, and acceptance that no
  longer parses historical advisory evaluation payloads.
- Updated the helper to freeze attempts, accept explicit selection, preserve
  claim verification locally, correct a review on the same attempt, and retry
  recoverable submissions while holding capability only in memory.
- Updated bundled skill guidance, browser DTOs, draft concerns, and smoke
  protocol assertion.
## Verification

- Focused API coverage: 29 passed, 1 skipped. Full API suite: 783 passed,
  2 skipped when run outside the sandbox; the earlier sandbox-only Playwright
  driver pipe failure did not reproduce.
- Ruff, Node skill tests (4 test modules), frontend lint/typecheck/architecture
  checks, codegen check, and `./dev.sh --smoke` passed. Frontend lint reports
  nine pre-existing warnings and no errors.
- Impeccable detector reported no findings for the updated draft panel.
## Follow-up

Tracker rebuild and validation completed with 0 errors and 7 documented,
pre-existing fork warnings.
