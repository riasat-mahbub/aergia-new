---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M1A456Z1PKM8CFYYW2BYE02B
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: riasat
CONFIDENCE: Medium
TAGS:
- tailoring
- agent
- protocol
- security
RELATIONS:
  supersedes:
  - FEAT-01M1A3ZJ4P4ZATYNSE4WP73ERD
AFFECTS:
  files:
  - contracts/
  - agent/
  - api/alembic/env.py
  - api/alembic/versions/g2h3i4j5k6l7_add_tailoring_sessions.py
  - api/app/app.py
  - api/app/models/user.py
  - api/app/models/application.py
  - api/app/models/cv.py
  - api/app/models/tailoring_session.py
  - api/app/schemas/tailoring.py
  - api/app/routes/tailoring.py
  - api/app/services/tailoring.py
  - api/tests/test_tailoring.py
  - api/tests/test_tailoring_contracts.py
  - web/src/lib/api/tailoring.ts
  - web/src/pages/ApplicationDetailPage.tsx
  - web/src/pages/__tests__/ApplicationDetailPage.test.tsx
LINKS:
  plan: local://2026-08-30-local-agent-tailoring.md
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-30T20:00:46.562043+00:00'
UPDATED_AT: '2026-08-30T20:00:46.562043+00:00'
---

# Local-agent CV tailoring protocol and workflow

## Background

Prototype committed as d085502. Focused contract, CLI, frontend, Ruff, build, metadata, and route checks pass; async SQLite integration remains blocked by the environment's Python 3.14 aiosqlite connection hang.

## Investigation

The committed Phase 1 implementation adds a separate capability boundary and
does not expose normal authentication tokens to the CLI. It is intentionally
limited to a linked CV, sanitized evidence, two fixed operations, and stored
requirement scoring. Existing unrelated relevance/extraction changes remain
outside the commit.

## Decision

Keep the generative-AI boundary narrow. The prototype invokes no LLM and adds
no provider credentials; existing server-side requirement extraction remains
unchanged. Rich-text policy, concurrency hashes, Career-Ops tools, and agent
reasoning remain later phases.

## Implementation

Commit `d085502` adds the tailoring-session migration/model, hashed one-time
code exchange, scoped evidence and submit routes, strict v1 contracts,
copy-on-write patching, persisted reported gaps, a fixed Node CLI, a minimal
web trigger, and focused tests.

## Verification

Passing: changed-file Ruff, seven no-conftest backend contract/copy-on-write
tests, CLI tests, full frontend Vitest (352 tests), frontend build, route and
metadata checks, and diff checks. Full async integration cannot run in the
current Python 3.14 environment because `aiosqlite.connect()` hangs before
database initialization. `npm run codegen:check` also remains unavailable
because `api/scripts/codegen_schema.py` is absent; full frontend lint retains
77 pre-existing explicit-`any` errors.

## Follow-up

Run `api/tests/test_tailoring.py` under the supported Python runtime and
complete the remaining phases from the plan before marking the feature done.
