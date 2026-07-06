---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KZHR806TYQPTPEFG5JE8879C
TYPE: task
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: riasat
CONFIDENCE: Medium
TAGS:
- phase-8
- hardening
- verification
RELATIONS:
  related:
  - EPIC-01KZCCC3MTXDGPY31H06NFYP1Q
AFFECTS:
  files:
  - dev.sh
  - scripts/smoke.sh
  - api/tests/test_devscript.py
  - api/tests/test_smoke_live.py
  - api/scripts/smoke_live.py
  - web/vite.config.ts
  - web/src/lib/test/viteConfig.test.ts
  - web/src/components/__tests__/ExportPDFButton.test.tsx
  - web/eslint.config.js
  - web/package.json
  - web/package-lock.json
  - PHASE_7_PROMPT.md
  - PLAN.md
  - AGENTS.md
  - local://phase-7-ast-pipeline-closeout.md
LINKS:
  plan: local://phase-7-closeout-phase-8-hardening-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-08T22:35:06.842263+00:00'
UPDATED_AT: '2026-08-08T22:35:06.842263+00:00'
---

# Phase 8 hardening gate

## Background

Close the shipped Phase 7 tracker docket, repair Vitest/ESLint verification blockers, and add a deterministic `./dev.sh --smoke` full-stack gate without changing renderer or customization schemas. The behavior reachable from the developer surface is the new `dev.sh --smoke` command: a temporary SQLite + built-SPA + live preview/PDF/HTML pass for `generic-modern`, `generic-classic`, and `generic-minimal`.

## Investigation

- Plan reference: `local://phase-7-closeout-phase-8-hardening-plan.md`.
- Tracker state at task creation: 16 errors and 35 warnings; AST-pipeline docket and Phase 6 records still show `PLANNED` / `IN_PROGRESS` / `PROPOSED`. Malformed lowercase-frontmatter feature/ADR records and duplicate-ID Phase-2 bugs cannot be addressed through `tracker close`; they must be migrated to fresh SCHEMA-3 entries and moved to `tracker-legacy/phase-7/`.
- Vitest currently discovers `web/node_modules_bak/zod` and reports `ERR_MODULE_NOT_FOUND` from `npm run lint` because `eslint-plugin-react-hooks` is missing from `web/package.json` even though `web/eslint.config.js` imports it.
- `dev.sh` lacks any non-server verification gate; existing `api/tests/test_devscript.py` only covers the uvicorn launcher.

## Decision

Hardening is the selected Phase 8 behavior. It touches verification, documentation, and tracker wiring only. No Pydantic schema, generated TypeScript, manifest vocabulary, resolver contract, `RenderModel`, renderer, or customize-panel payload changes.

## Implementation

Steps 1–7 of the plan; see `local://phase-7-closeout-phase-8-hardening-plan.md`. The first commits to be authored under `feat/ast-pipeline` are: vitest include + react-hooks plugin, ExportPDFButton tests, `scripts/smoke.sh` and dev.sh `--smoke` dispatcher, smoke-live client + tests, then tracker migration + closeout + closeout doc + AGENTS/PLAN/PHASE_7 prompt edits. Each commit keeps the build green.

## Verification

`./dev.sh --smoke` exits 0 with the line `SMOKE OK: modern/classic/minimal preview + PDF + built SPA`. `tracker rebuild && tracker validate` reports zero errors.

## Follow-up

Deferred behaviors (DOCX renderer, multi-template preview, asset upload UI) are recorded in `local://phase-7-ast-pipeline-closeout.md` with explicit dispositions.
