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
- P02: implementation running after reviewed contract/codegen.
- P03: implementation running; original PDF measurements saved in
  `docs/fixtures/minimal-readability/baseline.json`. Update old v3 test assertion
  in owned scanner-backfill tests and verify final PDF/freshness behavior.
- P04: pending integration; read-only Luna review.
- Release checks: pending implementation.

## Resume instructions

Read this file and the plan before restarting work. Inspect `git status` and
any `/tmp/minimal-pNN-handoff.md` files. Preserve existing untracked audit,
plan, and tracker files. Do not redo a packet whose completed checks are
recorded here. Root coordinates schema generation, tracker history, integration
checks, and this checkpoint file. At most three children run concurrently.

No deployment or merge has occurred. Checkpoints are durable workspace state;
they do not imply that partial changes are release-ready.
