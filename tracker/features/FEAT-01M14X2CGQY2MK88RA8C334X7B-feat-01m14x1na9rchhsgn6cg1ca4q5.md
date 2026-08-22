---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M14X2CGQY2MK88RA8C334X7B
TYPE: feature
STATUS: DONE
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
  supersedes:
  - FEAT-01M14X1NA9RCHHSGN6CG1CA4Q5
  related:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN98
  - FEAT-01M0ZNN9JBFNT5PKVGF8NBANZE
AFFECTS:
  files:
  - web/src/components/preview/UserTemplateRenderer.tsx
  - web/src/components/preview/pageGeometry.ts
  - web/src/components/preview/pagePagination.ts
  - web/src/components/preview/__tests__/UserTemplateRenderer.test.tsx
  - web/src/components/preview/__tests__/pagePagination.test.ts
  - web/src/pages/BuilderPage.tsx
  - api/app/services/renderer/html.py
  - api/tests/test_html_renderer.py
LINKS: null
VERIFIED_BY: Codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-28T19:20:41.751544+00:00'
UPDATED_AT: '2026-08-28T19:20:41.751544+00:00'
---

# Strong-approximation page pagination in live preview

## Background

The former preview inferred pages from continuous `body.scrollHeight` and
drew a line at a rounded 1122px interval. That diverged from the A4 PDF when
the editor pane narrowed the layout or Chromium moved an entry to preserve
print-flow constraints. The temporary implementation plan was removed after
the feature shipped; this entry is the durable record.

## Investigation

The PDF path remains the canonical Python HTML renderer plus Playwright
Chromium. Exact print fragments are not exposed to the live iframe DOM, so
pixel-perfect parity is not viable without a PDF-backed preview. A strong
approximation can still reproduce the renderer's known page-flow units and
keep the PDF pipeline unchanged.

## Decision

Use fixed A4 geometry at 96 CSS DPI: 210mm × 297mm (793.701px ×
1122.520px), with the renderer's 24px print top margin represented in the
preview. Scale only the outer visual canvas when the pane is narrow; never
change the iframe's internal layout width. Keep pagination preview-only and
document the remaining line-level widow/orphan and browser-fragmentation
limitations.

## Implementation

Commit `5853025` adds:

- `pageGeometry.ts` as the shared A4 geometry/scaling source.
- Non-visual `data-preview-*` flow metadata on renderer zones, sections, and
  entries, carrying resolved break-before, heading-with-first, and
  keep-together facts without changing PDF styling.
- `pagePagination.ts`, which measures each zone's flow units and inserts
  idempotent preview-only spacers for explicit breaks and supported
  keep-together moves. Entries taller than one printable page remain
  splittable.
- Font/image settling, two animation frames, and `ResizeObserver` reruns in
  `UserTemplateRenderer`, plus exact physical page labels on the shared
  scaled canvas.
- Pure packing tests, DOM spacer-idempotence tests, fixed-width component
  coverage, and renderer metadata/style-attribute regression coverage.

The PDF renderer and Playwright PDF options were not changed.

## Verification

Passed:

- Frontend Vitest: 53 files, 337 tests.
- Targeted backend renderer/PDF smoke: 48 tests; Ruff and codegen drift
  checks passed.
- Production frontend build and the smoke ESLint configuration passed.
- Direct authenticated Chromium smoke against the built SPA confirmed a
  793.701px layout width / 794px content viewport, narrow-pane visual scaling,
  measured preview spacers, and page-start labels; authenticated preview HTML
  and PDF export both remained valid.
- `tracker rebuild && tracker validate`: 356 entries, 0 errors, 2 existing
  fork warnings.

The aggregate `./dev.sh --smoke` gate still stops before live rendering on
four unrelated pre-existing asset/status test failures; no pagination failure
was observed.

## Follow-up

Exact parity would require rendering the existing Chromium PDF (or an
equivalent print-fragment service) as the preview surface. Revisit only if
line-level print fidelity becomes a product requirement.
