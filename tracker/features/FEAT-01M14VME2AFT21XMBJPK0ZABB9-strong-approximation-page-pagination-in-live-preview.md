---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M14VME2AFT21XMBJPK0ZABB9
TYPE: feature
STATUS: PLANNED
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: High
TAGS:
- preview
- pagination
- a4
- pdf
- ux
RELATIONS:
  related:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN98
  - FEAT-01M0ZNN9JBFNT5PKVGF8NBANZE
AFFECTS:
  files:
  - docs/plans/2026-08-28-strong-preview-pagination-approximation.md
  - web/src/components/preview/UserTemplateRenderer.tsx
  - web/src/components/preview/pageGeometry.ts
  - web/src/components/preview/pagePagination.ts
  - web/src/components/preview/__tests__/UserTemplateRenderer.test.tsx
  - web/src/components/preview/__tests__/pagePagination.test.ts
  - web/src/pages/BuilderPage.tsx
  - api/app/services/renderer/html.py
  - api/tests/test_html_renderer.py
  - api/tests/test_smoke_live.py
LINKS:
  plan: local://2026-08-28-strong-preview-pagination-approximation.md
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-28T18:55:36.010249+00:00'
UPDATED_AT: '2026-08-28T18:55:36.010249+00:00'
---

# Strong-approximation page pagination in live preview

## Background

The current live preview measures continuous screen-flow height and draws a
single fixed-height line per inferred page. It is not reliable when the pane
is narrower than A4 or when Chromium moves an entry because of
`break-inside: avoid` and related print-flow rules. A same-Chromium probe found
an A4-width case where the preview calculated four pages while the PDF had
five, plus a narrow-pane case where text wrapping changed the page content.

The implementation plan is recorded in
`docs/plans/2026-08-28-strong-preview-pagination-approximation.md`.

## Investigation

The existing PDF path is already canonical: `/render/html` and PDF export use
the same Python HTML renderer, while Playwright applies A4 print
fragmentation. The divergence begins after HTML generation:

- `UserTemplateRenderer` lays the iframe out at the available pane width.
- `body.scrollHeight` cannot see print-only unused space or fragment moves.
- The overlay uses rounded `1122px` geometry while the PDF uses A4 and a 24px
  top `@page` margin.

Exact browser-side introspection of Chromium's final print fragments is not
available. The chosen solution is therefore a fixed-width, measured,
preview-only paginator that explicitly approximates the renderer's known
page-flow rules.


## Decision

Use a fixed 210mm A4 iframe coordinate system, optionally scaled for a narrow
editor pane. Add stable renderer metadata for sections/entries, then run a
bounded client-side packing pass after fonts and images settle. Insert
preview-only spacers when an entry or explicit break would advance to the next
print page, and draw the existing boundary lines at exact A4 physical page
coordinates.

Keep the PDF pipeline unchanged. Do not call PDF generation on every editor
update. Do not claim exact parity for line-level widow/orphan behavior or
browser-specific fragmentation edge cases.


## Implementation

Planned phases and separate implementation/tracker commits:

1. `feat: fix live preview to fixed A4 geometry` /
   `tracker: record fixed A4 preview geometry`
2. `feat: expose preview pagination flow metadata` /
   `tracker: record preview pagination metadata`
3. `feat: add measured page packing to live preview` /
   `tracker: record measured preview page packing`
4. `test: verify strong preview pagination approximation` / tracker closeout

See the linked plan for phase files, pure paginator behavior, browser
regressions, acceptance criteria, and known risks.


## Verification

Planning verification completed:

- `tracker validate`: 353 entries, 0 errors, 2 pre-existing fork warnings.
- Same-Chromium probe confirmed the current height-only method can calculate
  four preview pages for a five-page PDF at A4 width.
- No runtime files were changed during the viability investigation.


## Follow-up

Implement the phases in order. Close the feature only after the browser smoke
compares wide/narrow preview layouts and the existing Playwright PDF output
for all three seed templates.
