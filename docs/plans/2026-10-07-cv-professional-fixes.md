# Classic and Minimal implementation checkpoints

Audit: [industry comparison](../cv-template-industry-comparison-2026-10-07.md).
Base: `d2529d7`. Branch: `feature/cv-template-professional-fixes`.
Tracker: `FEAT-01M4C690CDPWYMVBJZA0XN6QM0`.

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
(36 pt / half an inch). Zone widths use border-box sizing within the printable
area. Retain saved zone padding, including additional first/last-page vertical
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

P01/P02/P03 in progress. No release claim until the integration gate passes.

