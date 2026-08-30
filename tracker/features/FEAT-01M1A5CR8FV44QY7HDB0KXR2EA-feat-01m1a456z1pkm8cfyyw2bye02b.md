---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M1A5CR8FV44QY7HDB0KXR2EA
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
- planning
RELATIONS:
  supersedes:
  - FEAT-01M1A456Z1PKM8CFYYW2BYE02B
  depends_on:
  - FEAT-01M159T437M7QTNCEPRD4M0WHJ
  - FEAT-01M1899TYA2FS5PAT2T1GYC3KT
AFFECTS:
  files:
  - docs/plans/2026-08-30-local-agent-tailoring.md
  - contracts/
  - agent/
  - api/app/schema/models.py
  - api/app/models/cv.py
  - api/app/models/tailoring_session.py
  - api/app/schemas/tailoring.py
  - api/app/services/tailoring.py
  - api/app/services/tailoring_policy.py
  - api/app/services/tailoring_facts.py
  - api/app/routes/tailoring.py
  - api/alembic/versions/
  - api/tests/test_tailoring.py
  - api/tests/test_tailoring_contracts.py
  - api/tests/test_tailoring_facts.py
  - web/src/lib/api/tailoring.ts
  - web/src/pages/ApplicationDetailPage.tsx
LINKS:
  plan: local://2026-08-30-local-agent-tailoring.md
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-30T20:22:22.223359+00:00'
UPDATED_AT: '2026-08-30T20:22:22.223359+00:00'
---

# FEAT-01M1A456Z1PKM8CFYYW2BYE02B

## Background

Expanded the post-prototype plan into an execution-ready full implementation: verification baseline, explicit patch semantics, stable rich-text IDs, protected policy, CV revision/hash, server-owned provenance, Career-Ops safety adapters, manual Codex workspace, lifecycle UI, delivery gates, and revised effort.

## Investigation

The committed Phase 1 protocol is intentionally narrow and has no LLM or
Career-Ops dependency. A full implementation must preserve that boundary while
adding richer AST mutations. Aergia stores CV content as `SectionInstance`
data with rich-text blocks, and the current `CV.extra_metadata` is user-editable
so it cannot be authoritative provenance. Existing Library and relevance
records already expose entry/row IDs that can anchor an evidence scope.

The verification baseline is currently incomplete: the available Python 3.14
runtime hangs in `aiosqlite` setup, the documented schema codegen script is
absent, and full frontend lint has pre-existing failures. These need to be
separated from new tailoring failures before schema changes land.

## Decision

Deliver the robust version in four post-spike slices after a baseline gate:
patch semantics and server safety; Career-Ops-derived local/server validators;
manual Codex-first workspace; and UI lifecycle/hardening. Keep protocol version
1 for additive operations, advertise supported operations, and reserve a
protocol bump for breaking wire changes.

Use stable rich-text block/item IDs, explicit operation targets, a protected
field policy, canonical CV revision/hash compare-and-swap, and a server-owned
provenance representation. Validate and apply all changes in one transaction;
the server independently reruns important fact checks and relevance scoring.

## Implementation

The detailed execution plan is recorded in
`docs/plans/2026-08-30-local-agent-tailoring.md`. It covers:

1. restoring a trustworthy Python/SQLite integration and schema-codegen gate;
2. `rewrite_rich_text`, bullet/entry reorder/removal, and authoritative Library
   insertion with protected-field and stale-write rejection;
3. Aergia adapters for Career-Ops JD gap and fact checks, including MIT
   attribution and shared fixtures;
4. `prepare`, `validate`, and `submit` workspace commands with `SKILL.md`,
   read-only sources, bounded repair, cleanup, and manual `codex .` support;
5. expiry/cancel/retry/stale handling, before/after relevance, reported gaps,
   persisted results, and end-to-end hardening.

## Verification

Plan document updated after repository and Career-Ops inspection. No
implementation code was changed in this planning update.

## Follow-up

Implement one slice at a time and keep the fixed-patch acceptance flow green.
Do not mark the feature complete until stale/concurrent writes, protected facts,
server fact validation, provenance, workspace cleanup, and UI failure states
are covered by tests on the supported runtime.
