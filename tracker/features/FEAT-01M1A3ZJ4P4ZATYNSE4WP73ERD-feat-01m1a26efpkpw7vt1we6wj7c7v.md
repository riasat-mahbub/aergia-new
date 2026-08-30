---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M1A3ZJ4P4ZATYNSE4WP73ERD
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
  - FEAT-01M1A26EFPKPW7VT1WE6WJ7C7V
  related:
  - FEAT-01M136DNGK9NA50W2R9WB6QDBP
  - FEAT-01M159T437M7QTNCEPRD4M0WHJ
  - FEAT-01M129QBNK54QF2Y9PV8WDKN8N
  - FEAT-01M1899TYA2FS5PAT2T1GYC3KT
AFFECTS:
  files:
  - contracts/evidence-packet.schema.json
  - contracts/tailoring-patch.schema.json
  - contracts/fixtures/
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
CREATED_AT: '2026-08-30T19:57:41.398381+00:00'
UPDATED_AT: '2026-08-30T19:57:41.398381+00:00'
---

# Local-agent CV tailoring protocol and workflow

## Background

Implemented Phase 1 protocol prototype: scoped tailoring session and one-time capability exchange, sanitized evidence endpoint, strict v1 fixed patch operations, atomic server application with stored-requirement relevance refresh, CLI fixture client, minimal web session trigger, migration, contracts, and tests. Full async integration verification is blocked by a Python 3.14 aiosqlite connection hang in the current environment.

## Investigation

The Phase 1 prototype was implemented against the existing application, CV,
Library, profile, and deterministic relevance services. A dedicated session
model avoids normal JWT/refresh-token reuse, and the capability endpoints do
not expose user identity or database metadata to the CLI. The existing
relevance worktree changes were preserved.

## Decision

Keep the generative-AI boundary narrow: no generative inference or provider
credentials are introduced on the Aergia server. The first client is a fixed
protocol fixture, not an LLM adapter. Phase 1 supports only
`replace_description` for plain-string descriptions and `report_gap`, and it
scores with persisted application requirements.

## Implementation

Added the `tailoring_sessions` migration/model, hashed one-time exchange code
and scoped capability, strict protocol schemas/contracts, sanitized evidence
endpoint, atomic copy-on-write patch application, persisted reported gaps,
stored-requirement relevance refresh, fixed Node CLI, minimal web trigger, and
contract/integration tests. Rich text, protected-field policy, base hashes,
Career-Ops tools, agent workspace, and UI lifecycle are deferred to later
phases in the plan document.

## Verification

Passing focused checks:

- backend Ruff checks for changed files;
- seven no-conftest tailoring contract/copy-on-write tests;
- Node CLI tests;
- frontend Application detail test and full Vitest suite (352 tests);
- frontend production build;
- route/OpenAPI and synchronous SQLAlchemy metadata checks.

The full async tailoring integration file could not initialize in this
environment because `aiosqlite.connect()` hangs under local Python 3.14. The
failure occurs before the tests run and is independent of the tailoring code.
`npm run codegen:check` also remains unavailable because the repository does
not contain `api/scripts/codegen_schema.py`, and full frontend lint retains
the existing 77 explicit-`any` errors.

## Follow-up

Run the integration suite under the supported Python runtime before calling
Phase 1 production-ready. Then add base-hash concurrency, protected-field and
rich-text policy, Career-Ops fact fixtures, and workspace/UI lifecycle phases
as separate follow-up implementation steps.
