---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M29EXDVTJPBJCDR899Y3FYM1
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
  - FEAT-01M29DRR1Y8X15H3GC9ZBN301P
AFFECTS:
  files:
  - api/app/document_schema/capabilities.py
  - api/app/http_schemas/tailoring.py
  - api/app/models/cv.py
  - api/app/models/tailoring_session.py
  - api/app/services/tailoring.py
  - api/alembic/versions/m8n9o0p1_remove_tailoring_v1_session_state.py
  - api/tests/test_tailoring_contracts.py
  - api/tests/test_tailoring_session_migration.py
  - tailoring-skill/AGENTS.md
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - tailoring-skill/tests/session.test.mjs
  - web/src/features/applications/components/detail/GeneratedCvPanel.tsx
  - web/src/features/tailoring/
  - scripts/smoke.sh
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-12T00:05:13.211085+00:00'
UPDATED_AT: '2026-09-12T00:05:13.211085+00:00'
---

# FEAT-01M29DRR1Y8X15H3GC9ZBN301P

## Background

Final audit corrected v2 edge cases: generated drafts remain reviewable after agent capability expiry; profile fields absent from the account profile are stripped; source-CV deletion preserves the session; patch-only session columns are dropped and legacy applied sessions remain readable.

## Investigation

The cutover audit found that expiry applied to submitted drafts as well as
agent capabilities, profile fields missing from the account could be supplied
by the model, the source-CV relationship could cascade-delete a session, and
the capability descriptor still advertised v1 evidence locks. The skill also
mentioned inference notes inside the candidate even though the API schema
forbids that field. Finally, the release smoke script still asserted protocol
v1 and the deleted patch validator.

## Decision

Keep one-hour expiry scoped to agent credentials; an owner-visible submitted
draft remains reviewable. Treat only explicit profile identity fields as
server-owned and describe every other candidate field as editable. Remove
obsolete v1 session storage and preserve the source relationship with
``ON DELETE SET NULL``. Send uncertain-inference notes as bounded sidecar
metadata, not CV content.

## Implementation

Added a session cleanup migration that removes v1 evidence/patch columns,
normalizes the source-CV foreign key, and maps historical applied sessions to
the accepted state. Removed ORM ownership cascades that contradicted that FK.
Updated v2 capabilities, profile identity injection, review-note transport and
display, review response types, and the smoke bundle assertions. Added focused
contract and SQLite migration tests.

## Verification

Ruff, direct pure API/migration contract tests, Node skill tests, frontend
lint/typecheck/architecture checks, and codegen checks pass. The isolated smoke
runner completed backend lint, frontend lint, and production build, then timed
out during Alembic initialization at its 30-second guard under Python 3.14.
The existing full API pytest path has the same async SQLite startup hang.

## Follow-up

Rerun Alembic/API integration and the smoke gate under the supported Python
3.12 runtime; keep protocol-v1 migration downgrade intentionally irreversible.
