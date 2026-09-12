---
SCHEMA: 4
FORMAT: project-tracker
ID: ADR-01M29F1WXK02F3NYYQ5X6AECY3
TYPE: adr
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - ADR-01M29BGP0TN064SDB93RKRW7ST
  related:
  - FEAT-01M29EXDVTJPBJCDR899Y3FYM1
AFFECTS:
  files:
  - api/app/document_schema/capabilities.py
  - api/app/http_schemas/tailoring.py
  - api/app/models/tailoring_session.py
  - api/app/services/tailoring.py
  - api/app/routes/tailoring.py
  - api/alembic/versions/k6l7m8n9o0p1_move_section_overrides_into_instances.py
  - api/alembic/versions/l7m8n9o0p1_tailoring_v2_drafts.py
  - api/alembic/versions/m8n9o0p1_remove_tailoring_v1_session_state.py
  - api/tests/test_tailoring_contracts.py
  - api/tests/test_tailoring_session_migration.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - web/src/features/tailoring/
  - web/src/features/applications/components/detail/GeneratedCvPanel.tsx
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-12T00:07:39.699650+00:00'
UPDATED_AT: '2026-09-12T00:07:39.699650+00:00'
---

# ADR-01M29BGP0TN064SDB93RKRW7ST

## Background

Implemented the protocol-v2 decision on master: complete-candidate authoring, mutable canonical customization data, optional source context, unlinked draft creation, owner-only review, and protocol-v1 cleanup. Full smoke verification is recorded on the feature entry as deferred to Python 3.12 because Python 3.14 migration startup times out.

## Investigation


## Decision


## Implementation


## Verification

Focused API contract/migration tests and skill tests pass, as do frontend
typecheck, lint, architecture, and codegen checks. The release smoke gate
reached isolated Alembic initialization but timed out under Python 3.14; rerun
with the supported Python 3.12 runtime.

## Follow-up

Verify the full migration and live smoke flow under Python 3.12.
