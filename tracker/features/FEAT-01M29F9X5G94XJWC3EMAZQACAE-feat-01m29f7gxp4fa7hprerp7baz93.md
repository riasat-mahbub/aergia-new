---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M29F9X5G94XJWC3EMAZQACAE
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
  - FEAT-01M29F7GXP4FA7HPRERP7BAZ93
AFFECTS:
  files:
  - api/alembic/versions/m8n9o0p1_remove_tailoring_v1_session_state.py
  - api/tests/test_tailoring_session_migration.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-12T00:12:02.096749+00:00'
UPDATED_AT: '2026-09-12T00:12:02.096749+00:00'
---

# FEAT-01M29F7GXP4FA7HPRERP7BAZ93

## Background

Made the destructive v1 session cleanup migration explicitly refuse downgrade rather than leave Alembic reporting a schema that no longer contains the removed evidence fields; added a backup-required regression test.

## Investigation

The v1 session cleanup removes evidence and provenance fields that cannot be
reconstructed. A no-op Alembic downgrade would claim to restore the preceding
schema while leaving those columns absent.

## Decision

Refuse downgrade and require restoring a database backup to roll back across
this cutover.

## Implementation

The migration now raises a clear runtime error on downgrade, with a regression
test covering the refusal.

## Verification

Ruff and direct SQLite migration/downgrade contract tests pass.

## Follow-up
