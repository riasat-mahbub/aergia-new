---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M1A26EFPKPW7VT1WE6WJ7C7V
TYPE: feature
STATUS: PLANNED
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
  related:
  - FEAT-01M136DNGK9NA50W2R9WB6QDBP
  - FEAT-01M159T437M7QTNCEPRD4M0WHJ
  - FEAT-01M129QBNK54QF2Y9PV8WDKN8N
  - FEAT-01M1899TYA2FS5PAT2T1GYC3KT
AFFECTS:
  files:
  - docs/plans/2026-08-30-local-agent-tailoring.md
  - contracts/evidence-packet.schema.json
  - contracts/tailoring-patch.schema.json
  - contracts/fixtures/
  - agent/
  - api/app/models/tailoring_session.py
  - api/app/models/__init__.py
  - api/app/schemas/tailoring.py
  - api/app/routes/tailoring.py
  - api/app/services/tailoring.py
  - api/app/services/application.py
  - api/app/services/cv.py
  - api/app/services/relevance.py
  - api/app/core/rate_limit.py
  - api/alembic/versions/
  - api/tests/test_tailoring.py
  - api/tests/test_tailoring_contracts.py
  - api/tests/test_tailoring_facts.py
  - web/src/lib/api/tailoring.ts
  - web/src/lib/store/tailoringStore.ts
  - web/src/pages/ApplicationDetailPage.tsx
  - web/src/components/applications/
  - web/src/pages/__tests__/
LINKS:
  plan: local://2026-08-30-local-agent-tailoring.md
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-30T19:26:29.879025+00:00'
UPDATED_AT: '2026-08-30T19:26:29.879025+00:00'
---

# Local-agent CV tailoring protocol and workflow

## Background

Provide a local-agent CV tailoring flow: a short-lived scoped session, sanitized evidence packet, structured patch protocol, server-side validation and atomic application, deterministic relevance refresh, Career-Ops safety tooling, manual local-agent workspace, and UI lifecycle hardening. Generative AI and provider credentials remain outside Aergia production.

## Investigation

The repository already has the required domain primitives: applications store
job descriptions, linked CVs, stored relevance requirements, and relevance
results; generated CVs are materialized editable snapshots; and CV edits can
refresh linked application relevance. There is no tailoring-session model,
scoped capability, agent package, shared contract directory, or tailoring UI.

The existing CV update/relevance refresh path re-extracts job requirements.
Phase 1 must add a path that evaluates the persisted requirement snapshot so
the protocol acceptance test does not accidentally invoke extraction again.

The current section data boundary is intentionally flexible and rich text can
be represented as either legacy strings or structured blocks. Patch operations
therefore need a closed target/field policy and cannot trust arbitrary JSON
replacement data. Normal browser authentication is cookie-based; refresh
sessions are not suitable as tailoring capabilities.

The current working tree contains unrelated relevance and extraction changes;
implementation must preserve them.

## Decision

Use a five-phase implementation with a 9–15 focused engineer-day estimate.
The first useful internal prototype is the 4–6 day protocol slice.

The security boundary is generative AI and provider credentials: generative AI
runs under user-controlled credentials outside Aergia production. Existing
server-side GLiNER requirement extraction remains allowed. The agent receives
only a short-lived, task-scoped capability and sanitized evidence.

Phase 1 intentionally excludes Career-Ops, LLM reasoning, rich-text rewriting,
and automatic agent invocation. It supports only `replace_description` and
`report_gap`, targets an existing linked CV, uses a fixed patch, validates on
the server, applies atomically, and scores against stored requirements.

Later phases add the closed patch operation set, protected-field policy,
concurrency/provenance, Career-Ops-derived safety checks, a manual Codex
workspace, and UI lifecycle hardening.

## Implementation

Track the work in these independently verifiable phases:

1. **Protocol spike (2–3 days):** create the session and one-time code
   exchange, fetch a sanitized evidence packet, submit a fixed v1 patch, apply
   it atomically, and recompute using stored requirements.
2. **Patch semantics (2–3 days):** add rich-text and structural operations,
   protected fields, base hash/revision, provenance/evidence scope, strict
   contracts, and stale-write rejection.
3. **Career-Ops safety (2–4 days):** adapt JD-gap and fact-verification logic,
   add Aergia source adapters and shared fixtures, and retain MIT attribution.
4. **Agent workspace (1–2 days):** create the temporary `SKILL.md`, source,
   output, and tools workspace; support manual `codex .` use without an
   automatic adapter.
5. **UI and hardening (2–3 days):** add expiry, cancel/retry, stale-CV
   handling, result/gap presentation, before/after relevance, and security and
   end-to-end tests.

Do not add database synchronization, server-side generative inference, a
generic agent framework, or a chat interface.

## Verification

Phase 1's required integration flow is:

```text
create → exchange → evidence → submit → apply → score
```

It must cover ownership, expiry, replay, malformed operations, unknown target
IDs, bounded input, atomic rollback, and the updated relevance score. Later
verification adds protected-field attempts, stale hashes, rich-text fact
claims, Library provenance, repair-attempt limits, workspace cleanup, and UI
lifecycle coverage.

Run the focused protocol tests before the full smoke gate. The local
environment currently has known database/test-runtime instability, so that
baseline should not be confused with a protocol failure.

## Follow-up

Before implementation, confirm the final route names, evidence DTO, capability
exchange representation, and whether Phase 1 should capture a lightweight base
revision even though full stale-write enforcement is a Phase 2 deliverable.
