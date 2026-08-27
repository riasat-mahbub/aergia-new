---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNDS
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: riasat
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01M129QBNK54QF2Y9PV8WDKNDC
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-08T23:38:44.169337+00:00'
UPDATED_AT: '2026-08-08T23:38:44.169337+00:00'
---

# TASK-01KZHR806TYQPTPEFG5JE8879C

## Background

Closed 2026-08-08. ./dev.sh --smoke passes pytest (169), Ruff, source-only Vitest (203), React Hooks ESLint, production build, and isolated live preview/PDF checks for generic-modern, generic-classic, and generic-minimal with a fresh temporary SQLite DB. The Phase 7 tracker docket is closed; the closeout doc is local://phase-7-ast-pipeline-closeout.md. Remaining lint debt: the full eslint config reports pre-Phase-7 source issues (react-hooks refs/set-state-in-effect + @typescript-eslint) documented as Phase 9 work; the smoke gate enforces the React Hooks subset via eslint.config.smoke.js.

## Investigation


## Decision


## Implementation


## Verification


## Remaining tracker warnings

`tracker validate` reports 0 errors and 31 warnings after the closeout. The warnings are pre-existing historical debt outside the AST-pipeline docket and are intentionally not repaired:

- Forked supersede chains (pre-existing, unrelated to Phase 7): `BUG-01KZ48ABZ9DB96ANHPTJYF6NK0`, `TASK-01KYZCC3GT35RXGH0V1MK87CJ6`, `BUG-01KZ08THKAY2S6T6W2N3XMYWZX`.
- Non-ULID placeholder IDs on historical Phase-2/Phase-6 records that were imported with those IDs (`01KZJ0PHASE2QA`, `01KZPHASE6STEP1/2/3` prefixes) — the validator flags the ULID portion length but the records are valid chain roots superseded by real ULID successors created during this closeout.
- Broken slug-based RELATIONS on those historical records pointing at the migrated originals now in `tracker-legacy/phase-7/` (e.g. `FEAT-01KZCCM17NP6QSKMGG71QV4PWF-html-first-pipeline` no longer exists under `tracker/`).

These are documented, not swept, to preserve the append-only provenance of the imported historical chain.

## Follow-up

<!-- Migrated from TASK-01KZHVWG29MVF8VNSDADJ0TBPK during the schema-4 cutover. -->
