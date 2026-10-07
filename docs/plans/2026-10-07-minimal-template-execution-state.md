# Minimal template execution checkpoints

Plan: [Minimal readability](2026-10-07-minimal-template-readability.md).
Base: `b8e4016`. Execution started 2026-10-07.
Branch: `feat/minimal-readability`.
Active tracker head: `FEAT-01M4BY57VCRVC5QQ8HY66JC33T`.

## Current state

- P01: complete and reviewed. Optional schema, Minimal defaults, safe CSS vars,
  independent gaps, renderer version v4, compatibility/override tests implemented.
  Focused pytest: 107 passed; assigned-file Ruff and diff whitespace passed.
  Handoff: `/tmp/minimal-p01-handoff.md`.
- Codegen: generated schema refreshed; `npm run codegen:check` passed.
- P02: complete and reviewed. Inherited size/line height/gap hints added without
  storing defaults. Browser fixture covers open/edit/clear/reset/template switch
  and document-spacing precedence. Desktop/mobile captures inspected; detector,
  lint, typecheck, architecture checks passed. Existing RichTextToolbar lint
  warning remains. Handoff: `/tmp/minimal-p02-handoff.md`.
- P03: implementation running; original PDF measurements saved in
  `docs/fixtures/minimal-readability/baseline.json`. Update old v3 test assertion
  in owned scanner-backfill tests and verify final PDF/freshness behavior.
- P04: read-only Luna review running; final PDF evidence pending P03.
- Release checks: `./dev.sh --smoke` passed. Full backend pytest running;
  full backend Ruff and tailoring-skill Node tests passed (3 tests).

## Saved checkpoints

- `30667aa`: initial audit, plan, tracker, and execution-state checkpoint.
- `fb12368`: reviewed P01 renderer/schema/defaults plus generated web schema.

## Resume instructions

Read this file and the plan before restarting work. Inspect `git status` and
any `/tmp/minimal-pNN-handoff.md` files. Preserve existing untracked audit,
plan, and tracker files. Do not redo a packet whose completed checks are
recorded here. Root coordinates schema generation, tracker history, integration
checks, and this checkpoint file. At most three children run concurrently.

No deployment or merge has occurred. Checkpoints are durable workspace state;
they do not imply that partial changes are release-ready.
