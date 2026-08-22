# Strong approximation for live-preview PDF pagination

Tracker: `FEAT-01M14VME2AFT21XMBJPK0ZABB9`

## Objective

Replace the current height-only page-break overlay with a page-aware A4
preview that approximates the existing Chromium PDF pagination closely while
keeping the backend HTML renderer as the canonical document renderer.

The preview should continue to show the rendered HTML in an iframe. It should
also lay out content in a fixed A4 coordinate system, account for the
renderer’s page-flow rules, and draw the existing boundary lines at the
resulting physical page boundaries.

Exact parity remains out of scope for this feature. Chromium does not expose
its final print fragments to a normal browser page, so a PDF-backed preview is
the only exact solution and is intentionally deferred.

## Evidence and current failure

The current implementation in
`web/src/components/preview/UserTemplateRenderer.tsx` measures
`body.scrollHeight` and computes `Math.ceil(height / 1122)`. That assumes a
continuous screen layout packs every page completely.

A same-Chromium probe using the repository’s renderer and the exact PDF
options reproduced a concrete mismatch:

- At a 794px A4-width viewport, the preview body was 4,438px tall and the
  overlay calculated four pages; the generated PDF contained five pages.
- At a 672px editor-pane viewport, the preview body was 5,334px tall because
  text wrapped differently from the fixed-width A4 PDF. The PDF still had five
  pages in that sample, but the content-to-page assignments differed.

The mismatch is caused by three independent facts:

1. The preview width is responsive, while `page.pdf()` renders fixed A4.
2. Screen flow does not include the unused space created when
   `break-inside: avoid`, `break-before`, or heading/entry keep rules move a
   block to the next print page.
3. The overlay’s `1122px` constant is a rounded approximation of the exact
   A4 CSS height (`297mm = 1122.519685px`), and the PDF stylesheet currently
   reserves a 24px top margin on every printed page.

## Design decisions

### 1. Fixed A4 layout, visually scaled when necessary

The iframe’s layout width will always be 210mm (approximately 793.7 CSS px),
regardless of the editor pane width. When the pane is narrower, an outer
viewport may scale the completed A4 canvas for usability; the iframe itself
must not reflow to the scaled width. Horizontal scrolling remains available
as a fallback.

The preview geometry will use one frontend page-geometry module containing:

- A4 width and height in mm.
- Exact CSS-pixel conversion at 96dpi.
- The renderer’s 24px print top margin.
- The printable content height for each page.

The overlay and the pagination pass will consume these values instead of
independent magic numbers.

### 2. Screen preview mirrors print-page insets

The preview iframe will apply the print top inset to its screen-only body
layout. Page starts will therefore be represented as:

```text
page N physical top + 24px content inset
```

The PDF’s `@page` rule and the preview geometry will be covered by a backend
renderer test so a later print-margin change cannot silently invalidate the
preview.

### 3. Stable page-flow units

The HTML renderer will expose stable, non-visual attributes on sections and
entries, such as a page-flow unit identifier and the relevant resolved flow
flags. These attributes are metadata for the preview DOM only; they do not
change the generated PDF’s visual output.

The preview paginator will process units per zone, because the document has a
horizontal multi-zone layout and each zone has its own vertical flow. It will
honor, in order of importance:

- Explicit `break-before: page`.
- `break-inside: avoid` on entries that fit within one printable page.
- The heading-plus-first-entry keep relationship.
- Normal sequential flow when a unit fits in the remaining page space.
- Natural splitting for an entry taller than one printable page.

Orphan/widow behavior will remain best-effort. Exact line-level print
fragmentation is not available to the browser-side paginator and will be
documented as a known limitation.

### 4. Idempotent measured page packing

After the iframe document is written, the parent will wait for fonts, image
completion, and at least one settled layout frame before measuring. A
`ResizeObserver` will rerun the pass when content height changes.

The paginator will:

1. Remove only its own prior spacer/metadata nodes.
2. Measure the page-flow units at fixed A4 width.
3. Insert preview-only vertical spacers before units that must move to the
   next page.
4. Re-measure after insertion and stop when stable, with a bounded pass count
   to prevent feedback loops.
5. Return the highest page index reached and the final visual height.

The spacers create the blank space that Chromium’s print engine creates when
an entry is pushed forward by `break-inside: avoid`. This is the key change
from simply drawing a line over continuous content.

### 5. Boundary overlay remains preview-only

The existing dashed boundary line and page label remain outside the rendered
HTML and therefore cannot enter the PDF. Their positions will be based on the
fixed A4 physical page height and the paginator’s final page count. The line
will be inside the same visual canvas as the iframe so scaling and scrolling
cannot desynchronize it.

## Implementation phases

Each phase is independently verifiable. Implementation and tracker commits
remain separate, and the merge into `master` remains the cutover.

### Phase 1 — Establish fixed A4 preview geometry

Commit: `feat: fix live preview to fixed A4 geometry`

Files:

- `web/src/components/preview/UserTemplateRenderer.tsx`
- `web/src/pages/BuilderPage.tsx`
- new `web/src/components/preview/pageGeometry.ts`
- `web/src/components/preview/__tests__/UserTemplateRenderer.test.tsx`

Work:

- Replace the responsive iframe width with a fixed 210mm layout width.
- Add a scale-to-fit viewport or horizontal-scroll fallback without changing
  the iframe’s layout width.
- Replace `1122` with exact shared geometry values.
- Apply the 24px screen preview top inset.
- Keep the overlay preview-only and preserve its accessibility behavior.

Verification:

- Preview layout width is identical at wide and narrow editor pane widths.
- A long line wraps at the same A4 width in both pane sizes.
- Geometry unit tests cover exact page height, printable height, and scaling.
- `npm run test -- --run` for affected frontend tests.
- `npm run lint` and `npm run build`.

Tracker follow-up: update `FEAT-01M14VME2AFT21XMBJPK0ZABB9` to `IN_PROGRESS`
with the focused verification note, rebuild, validate, and commit the tracker
update separately as `tracker: record fixed A4 preview geometry`.

### Phase 2 — Add renderer flow metadata

Commit: `feat: expose preview pagination flow metadata`

Files:

- `api/app/services/renderer/html.py`
- `api/tests/test_html_renderer.py`
- `web/src/components/preview/pagePagination.ts`
- `web/src/components/preview/__tests__/pagePagination.test.ts`

Work:

- Add stable data attributes to rendered section/entry units.
- Carry only the resolved page-flow facts needed by the paginator.
- Keep attributes non-visual and ensure they do not alter PDF output.
- Add a pure paginator API that accepts measured units and page geometry, so
  most behavior can be tested without jsdom layout support.

Verification:

- Backend tests assert metadata appears on the correct units and does not
  change existing semantic markup.
- Pure pagination tests cover fit, move-to-next-page, explicit page break,
  heading-plus-first-entry grouping, multi-zone flow, and over-page entries.
- `pytest api/tests/test_html_renderer.py`.
- `ruff check .` and `npm run codegen:check` if model/wire types are touched.

Tracker follow-up: update the feature entry to `IN_PROGRESS`, rebuild,
validate, and commit `tracker: record preview pagination metadata`.

### Phase 3 — Integrate measured packing and boundaries

Commit: `feat: add measured page packing to live preview`

Files:

- `web/src/components/preview/UserTemplateRenderer.tsx`
- `web/src/components/preview/pagePagination.ts`
- `web/src/components/preview/__tests__/UserTemplateRenderer.test.tsx`
- `web/src/components/preview/__tests__/pagePagination.test.ts`

Work:

- Wait for fonts and images before the first measurement.
- Add bounded, idempotent spacer insertion and cleanup.
- Re-run on settled resize/content changes without allowing stale render
  responses or observer callbacks to overwrite newer HTML.
- Base iframe height and boundary count on the final packed layout, not just
  continuous body height.
- Keep the line labels and scrolling behavior aligned with the scaled canvas.

Verification:

- The previous four-versus-five-page regression fixture now shows five page
  boundaries in the preview.
- Entries protected by `break-inside: avoid` visibly move with the boundary
  instead of remaining above it in continuous flow.
- Explicit section breaks and tall-entry fallback are covered.
- Rerendering the same HTML is idempotent and does not accumulate spacers.
- `npm run test -- --run`, `npm run lint`, and `npm run build`.

Tracker follow-up: update, rebuild, validate, and commit
`tracker: record measured preview page packing`.

### Phase 4 — Browser regression and closeout

Commit: `test: verify strong preview pagination approximation`

Files:

- `api/tests/test_smoke_live.py` or a focused browser smoke test
- affected frontend tests
- this plan’s verification notes

Work:

- Exercise classic, modern, and minimal templates at wide and narrow pane
  widths.
- Compare preview page count and page-start unit assignments with PDFs made
  by the existing Playwright pipeline.
- Include explicit page breaks, keep-together entries, two-column zones,
  rich-text wrapping, and an entry taller than one page.
- Record known residual differences rather than asserting impossible exact
  parity for line-level widows/orphans.

Verification:

- Focused backend and frontend tests pass.
- `pytest`, `ruff check .`, `npm run test -- --run`, `npm run lint`, and
  `npm run build` pass.
- `./dev.sh --smoke` passes when Chromium prerequisites are available.
- Tracker is rebuilt and validates with no new errors.

Tracker follow-up: close the feature only after the browser regression is
verified; use a separate `tracker:` commit for the closeout update.

## Acceptance criteria

- The iframe always lays out at the same 210mm width used by the PDF.
- The preview shows one boundary per approximated physical PDF page, including
  pages created by keep-together rules that leave unused space.
- Entries moved to later pages in the PDF are also moved below the matching
  preview boundary in the normal supported cases.
- The overlay is never included in `/render/pdf` output.
- Font/image settling and repeated renders do not leave stale height, page
  count, or spacer state.
- The preview remains usable in a narrow pane through scaling or horizontal
  scrolling.
- Known limitations are documented: line-level widow/orphan decisions,
  browser-specific fragmentation edge cases, and entries taller than one page.

## Non-goals and risks

- Do not replace the backend HTML renderer with React rendering.
- Do not add a second PDF engine or change Playwright export semantics.
- Do not make the preview call PDF generation on every editor update.
- Do not promise exact parity for arbitrary HTML/CSS; if exact parity becomes a
  product requirement, revisit a PDF-backed preview using the existing
  Chromium output.
- Spacer insertion can interact with flex/grid and zone-specific margins;
  keep the paginator pure, bounded, and covered by real-browser tests.
