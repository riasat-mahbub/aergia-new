# Minimal template execution checkpoints

Plan: [Minimal readability](2026-10-07-minimal-template-readability.md).
Base: `b8e4016`. Execution started 2026-10-07.
Branch: `feat/minimal-readability`.
Tracker head: `FEAT-01M4C081M0P60SR7VFHE18KQDA` (**DONE**).
Status: **complete**. All packets used GPT-6 Luna with max reasoning.

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
- P04: independent read-only review complete, no outstanding product blockers.
  [Durable review](../fixtures/minimal-readability/review.md).
- Release checks: frozen backend suite **938 passed, 1 skipped**; full Ruff,
  frontend lint/typecheck/architecture checks, codegen check, tailoring-skill
  Node tests (3), and final `./dev.sh --smoke` passed. Tracker rebuild/validate
  passed: 716 entries, zero errors, seven unchanged historical fork warnings.

### Final integration gate

- P02 code checkpoint: `40ded69`. Follow-up fixture verifies production
  `updateInstanceStyle`, JSON serialization/remount, explicit body size and
  `entry_gap: none`, clearing/reset without stored inherited defaults.
- Current production audit artifacts: `/tmp/minimal-current-audit`. Minimal
  short/long: 1/2 pages, 10.5/12/18 pt, all ten local parser checks pass, no
  out-of-bounds glyphs. Classic/Modern PNGs match original baseline exactly;
  Modern's historical recovery warnings remain visible.
- Actual `UserTemplateRenderer` captures: `/tmp/minimal-preview-{short,long}.png`.
  Initial long-preview capture exposed a page marker crossing an entry kept
  together by export. Measuring the renderer's `.section-entries` container
  and compensating the extra flex gap fixes it. Final capture has one spacer,
  no crossing entries, and the same page-two starting job heading as export.
  The self-contained browser regression regenerates HTML/PDF through the
  production renderer from committed synthetic fixtures; it uses the API
  virtualenv and existing PDFium dependency. Both browser fixtures pass.
- Backend full runs exposed only new-test measurement/fixture defects; P03
  corrected them before the passing frozen run: `/tmp/minimal-frozen-pytest.log`.
- Final smoke log: `/tmp/minimal-final-smoke.log`. No merge or deployment occurred.

## Saved checkpoints

- `30667aa`: initial audit, plan, tracker, and execution-state checkpoint.
- `fb12368`: reviewed P01 renderer/schema/defaults plus generated web schema.
- `40ded69`: reviewed builder inheritance hints and browser behavior fixture.
- `a9ede43`: PDF, legacy, freshness, and persistence regressions plus evidence.
- Final checkpoint: preview correction, self-contained pagination regression,
  review, tracker completion, and this execution report (commit containing it).

## Resume instructions

No implementation work remains. Read this file, the plan, and the fixture
README before any future continuation. Do not repeat completed checks without
a new change or concern. Temporary images can be regenerated with the recorded
fixture commands; synthetic measurements and review are committed.

External vendor ATS acceptance was not tested. Existing Modern recovery
warnings and the RichTextToolbar lint warning remain. The review notes a minor
API roundtrip coverage limitation for individual body-size/gap tokens.
