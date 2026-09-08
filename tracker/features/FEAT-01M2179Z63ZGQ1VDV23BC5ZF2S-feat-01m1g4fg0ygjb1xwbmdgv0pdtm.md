---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2179Z63ZGQ1VDV23BC5ZF2S
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: riasat
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M1G4FG0YGJB1XWBMDGV0PDTM
AFFECTS:
  files:
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - tailoring-skill/skills/aergia-tailor/scripts/jd-check.mjs
  - tailoring-skill/skills/aergia-tailor/scripts/validate-patch.mjs
  - tailoring-skill/skills/aergia-tailor/scripts/verify-cv-facts.mjs
  - tailoring-skill/skills/aergia-tailor/references/evidence-packet.schema.json
  - tailoring-skill/skills/aergia-tailor/references/tailoring-patch.schema.json
  - api/app/services/tailoring_skill.py
  - api/app/services/tailoring.py
  - api/app/http_schemas/tailoring.py
  - api/app/routes/tailoring.py
  - web/src/features/tailoring/pages/TailoringSessionPage.tsx
  - web/src/features/tailoring/types/index.ts
  - web/src/features/applications/components/detail/GeneratedCvPanel.tsx
  - scripts/smoke.sh
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-08T19:18:20.099763+00:00'
UPDATED_AT: '2026-09-08T19:18:20.099763+00:00'
---

# FEAT-01M1G4FG0YGJB1XWBMDGV0PDTM

## Background

Audited and repaired the local-agent tailoring path: made aergia-tailor a metadata-valid self-contained skill, added a same-origin downloadable bundle and web install affordances, added an in-memory capability session helper, fixed local patch materialization and stale fixtures, expanded requirement checks beyond a fixed vocabulary, increased scoped session TTL to one hour, and removed the contradictory 100-container Library cap while retaining evidence/fact/profile safety boundaries.

## Investigation

The install prompt named an unspecified official source, the skill lacked YAML
metadata, and its required tools/contracts lived outside the directory users
would install. The local validator also did not materialize most operations,
the valid fixture targeted the source CV instead of the fresh target, and the
manual exchange flow could not retain a capability without exposing or
persisting it. The 15-minute TTL and 100-Library-container response cap created
additional failures unrelated to the server's evidence safety policy.

## Decision

Keep protocol v1 and its immutable-profile and evidence-backed-fact boundaries.
Package all runtime assets under one valid skill folder, serve that folder as a
same-origin ZIP, and let a persistent helper own the scoped capability in
memory. Express tailoring as an outcome with broad structural discretion rather
than a rigid attempt-count workflow.

## Implementation

Added skill metadata/resources, an in-memory session helper, complete local
patch materialization, open-ended stored-requirement checks, a deterministic
public ZIP endpoint, prompt/UI install links, production image packaging, a
one-hour session TTL, and full Library-container evidence delivery.

## Verification

Skill quick validation, Node safety tests, Ruff, frontend lint/typecheck,
architecture fixtures/check, codegen drift, production web build, direct ASGI
bundle download, OpenAPI checks, Pydantic fixtures, and materialized fact checks
pass. The release smoke reaches the live stage but the documented Python
3.14/aiosqlite Alembic migration hang times out after 30 seconds; pytest has the
same pre-collection hang.

## Follow-up

Run the full pytest and live smoke gates once the repository moves off the
incompatible Python 3.14 async-SQLite environment.
