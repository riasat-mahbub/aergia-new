# Classic and Minimal implementation checkpoints

Audit: [industry comparison](../cv-template-industry-comparison-2026-10-07.md).
Base: `d2529d7`. Branch: `feature/cv-template-professional-fixes`.
Tracker root: `FEAT-01M4C690CDPWYMVBJZA0XN6QM0`.
Tracker head: `FEAT-01M4C7AF6Y2352ZNN4071088DB` (**DONE**).

## Scope and ownership

All implementation packets use GPT-6 Luna at max reasoning. The coordinator
reviews their results and owns integration, tracking, checkpoints and cutover.

- P01 (`cv_defaults_dates`): Classic body/line-height and entry/field defaults;
  clear date ranges; supported-format scanner guidance; focused regressions.
- P02 (`cv_margins_preview`): repeating physical PDF margins, matching preview
  geometry/pagination, renderer freshness, oversized-entry advice; production
  PDF and preview regressions.
- P03 (`minimal_p04`, reused Luna max agent): backward-compatible profile
  `show_urls` option, visible compact destinations, generated contracts,
  factual writing prompts and persistence/extraction/UI checks.

Keep authored styles, zone padding and labels effective. No automatic content
rewriting, page-count enforcement, or text shrinking. Larger optional audit
ideas (DOCX, regional paper sizes, academic/career-stage structures and tagged
PDF output) are outside this patch.

## Geometry decision

Use physical A4 margins of 48 CSS px top/bottom and 16 CSS px left/right.
The standard 32 px zone inset makes the default horizontal text inset 48 px
(36 pt / half an inch). Single-zone widths use border-box sizing within the
printable area. Modern retains its existing multi-zone content-box flex sizing:
applying border-box there narrowed its sidebar enough to break URL recovery.
Retain saved zone padding, including additional first/last-page vertical
space and explicitly tighter custom horizontal padding. Preview uses the same
printable width and top/bottom content boundaries.

## Checkpoints

1. Plan and task allocation recorded; packets implementing.
2. Review focused results and combined source diff; resolve integration issues.
3. Freeze the combined implementation and run backend, frontend, codegen,
   architecture, tailoring and smoke release checks; inspect actual PDF/UI.
4. Save verification evidence and tracker completion, commit the feature and
   merge into `master` using a regular merge commit. No remote deployment.

## Current state

- P01 complete: 161 focused API checks pass; date unit tests and typecheck
  pass. Classic default and authored-override regressions are included.
- P02 complete: short/long/saved-custom preview counts and page-two starts
  agree with export; bottom-margin boundary checks pass. The ResizeObserver
  registers once and settles after one callback per fixture. Mobile preview
  has no horizontal overflow. Oversized entries receive a named advisory;
  their line-level pagination remains approximate (stress fixture: preview
  five pages, PDF six), so the notice does not promise exact page count.
- P03 complete: five API/PDF checks plus desktop/mobile keyboard and
  save/remount checks pass. Both local parsers recover opt-in destinations;
  full clickable URIs remain intact. New helper text uses `app-ink-2` to meet
  contrast on the existing canvas and muted surfaces.
- Integration: first smoke gate passed. The first full backend run found four
  Modern URL recovery regressions and an obsolete stress-fixture edge-position
  assertion. Narrowing border-box to single zones restored recovery; updating
  the edge assertion retains physical margins and role/date/body attachment.
  All 69 affected checks pass; the new normal long fixture also verifies every
  role/company/first-and-last-bullet group stays together across reflow.
  The URL preference is included in both owner-contact normalization and
  render-basis freshness; focused precedence/freshness regressions pass.
  Final backend/smoke gates passed against corrected checkpoint `02f4fd6`:
  **978 passed, one skipped**; smoke Ruff, frontend lint/build, isolated
  migrations, Start/API gateway, SSR/security and auth checks passed.
  Full frontend lint and
  typecheck, architecture fixtures/check, codegen check, and three tailoring
  tests pass. Existing RichTextToolbar dependency warning remains.
- Independent read-only integration review by the P01 agent found no remaining
  blocker; [review and measurements](../fixtures/cv-professional-fixes/README.md)
  are saved as durable evidence.

Implementation and verification are complete. Saved checkpoints: `f5c7ab0`
(plan/task allocation) and `02f4fd6` (reviewed implementation). The final
verification/tracker checkpoint is followed by a regular local merge into
`master`. No remote push or deployment is part of this task.

Temporary packet handoffs:
`/tmp/cv-defaults-dates-handoff.md`, `/tmp/cv-links-prompts-handoff.md`, and
`/tmp/cv-margins-preview-handoff.md`.
