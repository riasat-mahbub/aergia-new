---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M3B2RC3PNM26Q853X2JYTZWV
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M3B1011B5J0QN4501Y1N9FC6
AFFECTS:
  files:
  - api/app/services/tailoring.py
  - api/app/http_schemas/tailoring.py
  - api/app/services/library.py
  - api/alembic/versions/v0w1x2y3_full_history_tailoring_v9.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - web/src/features/tailoring/types/index.ts
  - scripts/smoke.sh
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-25T01:26:55.350381+00:00'
UPDATED_AT: '2026-09-25T01:26:55.350381+00:00'
---

# FEAT-01M3B1011B5J0QN4501Y1N9FC6

## Background

Implemented and verified full-history protocol v9; release smoke passed with localhost access.

## Investigation


## Decision


## Implementation

Protocol v9 supplies a full plaintext dossier, a canonical preview candidate,
and direct evaluated-candidate submission. Semantic indexing/retrieval and the
required editorial-review protocol were removed across backend, skill, web,
docs, tests, and migration. Historical owner draft review remains supported.

## Verification

Release smoke passed with localhost access; focused backend tests passed (70),
skill tests passed (8), and web lint/typecheck/architecture/codegen passed.
Full backend suite: 764 passed, 1 skipped, with one Playwright driver startup
failure under the restricted sandbox; that PDF test passed when rerun with
local access. Migration upgrade/downgrade/upgrade passed.

## Follow-up
