---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M1A82B9AAMKSV2PX2KG4QWRF
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
- safety
- concurrency
- provenance
- implementation
RELATIONS:
  supersedes:
  - FEAT-01M1A5CR8FV44QY7HDB0KXR2EA
  depends_on:
  - FEAT-01M159T437M7QTNCEPRD4M0WHJ
  - FEAT-01M1899TYA2FS5PAT2T1GYC3KT
AFFECTS:
  files:
  - agent/
  - contracts/
  - api/alembic/versions/h3i4j5k6l7_add_tailoring_patch_safety.py
  - api/app/models/cv.py
  - api/app/models/tailoring_session.py
  - api/app/routes/tailoring.py
  - api/app/schema/models.py
  - api/app/schemas/tailoring.py
  - api/app/services/cv.py
  - api/app/services/rich_text.py
  - api/app/services/tailoring.py
  - api/app/services/tailoring_policy.py
  - api/scripts/codegen_schema.py
  - api/tests/test_tailoring.py
  - api/tests/test_tailoring_contracts.py
  - web/src/generated/schema.ts
LINKS:
  plan: local://2026-08-30-local-agent-tailoring.md
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-30T21:09:06.986728+00:00'
UPDATED_AT: '2026-08-30T21:09:06.986728+00:00'
---

# FEAT-01M1A5CR8FV44QY7HDB0KXR2EA

## Background

Implemented the Phase 0/2 foundation: restored schema codegen, canonical rich-text IDs, versioned patch operations, protected-path policy, CV revision/hash CAS, Library evidence snapshots, provenance persistence, and focused operation tests. Full async integration remains blocked by the Python 3.14/aiosqlite startup hang; existing relevance edits remain separate.

## Investigation

The protocol now targets the existing linked CV and continues to keep
generative inference and provider credentials outside Aergia. Rich-text
blocks/items previously had no stable target IDs, so the normalizer assigns
IDs on CV writes and session creation. Library content is snapshotted by
hash; source rows are resolved again by the server at submission time.

## Decision

Keep protocol version 1 and make the six Phase 2 mutations additive. Use
explicit section/entry/block/item IDs, a server-generated ID for Library
insertions, a protected-path policy, and CV revision/hash compare-and-swap.
Persist patch provenance and gaps on the tailoring session. The server still
owns final validation, relevance calculation, and the transaction.

## Implementation

Added strict Pydantic and JSON Schema contracts for rich-text rewrites,
bullet/entry removal and reordering, Library insertion, snapshot identity,
evidence references, and provenance. Added the CV revision migration, copy-
on-write patch handlers, policy delta validation, authoritative Library row
copying, and CLI operation-advertisement checks. Restored the documented
Pydantic-to-TypeScript codegen script and regenerated the rich-text types.

## Verification

The focused backend contract/codegen/parser tests pass (38 tests), the full
frontend Vitest suite passes (352 tests), the frontend production build
passes, the CLI test passes, Ruff and Python compilation pass, and all JSON
contracts parse. Full async pytest/migration startup was attempted with an
8-second timeout and remains blocked before tests execute by the available
Python 3.14/aiosqlite connection hang. Full frontend lint still reports the
repository's pre-existing `any` errors outside this slice.

## Follow-up

Run the integration suite under the supported Python 3.12 runtime before
merging. Then implement Career-Ops-derived JD/fact safety tools, the manual
Codex workspace, and UI lifecycle hardening from the linked plan. Add stale,
concurrent-submit, rollback, and server fact-validation integration tests.
