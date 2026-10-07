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
- P03: complete, reviewed, and frozen. 25 focused tests and assigned-file Ruff
  passed. Measurements and parser comparison saved under
  `docs/fixtures/minimal-readability/`; handoff `/tmp/minimal-p03-handoff.md`.
- P04: read-only Luna review running; final PDF evidence pending P03.
- Release checks: `./dev.sh --smoke` passed. Full backend pytest running;
  full backend Ruff and tailoring-skill Node tests passed (3 tests).

### Final integration gate

- P02 code checkpoint: `40ded69`. Follow-up fixture verifies production
  `updateInstanceStyle`, JSON serialization/remount, explicit body size and
  `entry_gap: none`, clearing/reset without stored inherited defaults.
- Current production audit artifacts: `/tmp/minimal-current-audit`. Minimal
  short/long: 1/2 pages, 10.5/12/18 pt, all ten local parser checks pass, no
  out-of-bounds glyphs. Classic/Modern PNGs match original baseline exactly;
  Modern's historical recovery warnings remain visible.
- Actual `UserTemplateRenderer` captures: `/tmp/minimal-preview-{short,long}.png`.
  Typography, gaps, and page counts match, but the long preview page marker
  crosses an entry kept together by export. P04 traced this to preview
  measurement looking for direct section entries instead of the renderer's
  `.section-entries` wrapper. P02 owns a bounded adapter fix/regression now.
- Backend full runs exposed only new-test measurement/fixture defects; P03
  corrected them. Frozen-tree full run: `/tmp/minimal-frozen-pytest.log`.
  Do not report the complete suite passed until a final frozen-tree run passes.
- Current gate is incomplete; no merge or deployment is authorized/performed.

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
