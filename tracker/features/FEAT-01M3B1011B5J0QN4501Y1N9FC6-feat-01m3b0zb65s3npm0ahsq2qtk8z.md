---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M3B1011B5J0QN4501Y1N9FC6
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
  - FEAT-01M3B0ZB65S3NPM0AHSQ2QTK8Z
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
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-25T00:56:09.003802+00:00'
UPDATED_AT: '2026-09-25T00:56:09.003802+00:00'
---

# FEAT-01M3B0ZB65S3NPM0AHSQ2QTK8Z

## Background

Implementation delegated across backend, portable skill, and frontend/test workstreams on feature/full-history-tailoring.

## Investigation

The index and semantic path had no independent active product reader. Library writes
maintained derived rows for tailoring. The new dossier reads every authoritative
profile and Library row directly, with stable source labels and raw narratives.

## Decision

Use protocol v9 with creation, preview, editing, and agent-selected submission.
Keep backend validation, rendering, scanner advice, stale-context checks, the
five-preview limit, and evaluation/hash binding. Remove the required structured
editorial-review stage and its local validator. Retain historical draft review.

## Implementation

Removed semantic index, proposition, opportunity, and retrieval code and tables;
added a migration with downgrade support. Context now carries the complete
plaintext dossier and template constraints. Preview returns the canonical
candidate so submit can send the exact evaluated document. Updated the portable
skill, helper, web contract and copy, docs, tests, and release smoke assertions.

## Verification

Full release smoke passed with localhost access. Backend focused suite: 70
passed. Full backend suite: 764 passed, 1 skipped, 1 Playwright-driver startup
failure in the restricted sandbox. Skill tests: 8 passed. Web lint, typecheck,
architecture tests/check, codegen check, Ruff, and migration
upgrade/downgrade/upgrade passed. Git diff whitespace check passed.

## Follow-up
