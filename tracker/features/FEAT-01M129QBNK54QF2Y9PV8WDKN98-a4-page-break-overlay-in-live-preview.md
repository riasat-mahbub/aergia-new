---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN98
TYPE: feature
STATUS: DONE
SUMMARY: A4 page-break rules drawn across the live preview iframe so the user can
  see where the PDF will cut
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: High
TAGS:
- preview
- builder
- ux
RELATIONS:
  related:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN85
AFFECTS:
  files:
  - web/src/components/preview/UserTemplateRenderer.tsx
LINKS: null
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-03T15:30:00+00:00'
UPDATED_AT: '2026-08-03T15:30:00+00:00'
---

# A4 page-break overlay in the live preview

## Background

The live preview in `BuilderPage` rendered the CV inside an iframe clipped to a single A4 page (`h-[297mm]`). Content past 297mm was hidden, so the user had no way to see where the next page would start in the exported PDF. The user asked for a page-break overlay: a thin horizontal rule at every 297mm offset across the full document height, always on, preview-only (not persisted, not in the PDF).

## Decision

Two coupled changes in `web/src/components/preview/UserTemplateRenderer.tsx`:

1. **Measure the iframe's natural content height.** After each `iframeDoc.write(html)`, schedule a `requestAnimationFrame` that reads `iframeDoc.body.scrollHeight` and stores it in a new `useState<number>` (`iframeHeight`, default `PAGE_HEIGHT_PX = 1122`). The iframe's CSS `height` is bound to that state, so the iframe grows to fit all pages. The parent `overflow-y-auto` wrapper in `BuilderPage.tsx:488` already handles scrolling for tall content.

2. **Draw dashed rose page-break rules.** Convert the iframe wrapper to `position: relative` and add `pages - 1` absolutely-positioned `<div>`s, each with a 1px dashed `border-rose-400` top edge and a "Page N starts" badge. The first rule sits at `top: 1122px`, the second at `2244px`, etc. — exactly where Chromium's print engine will cut, because `PAGE_HEIGHT_PX = 1122` is 297mm at 96dpi and matches `@page { size: A4; margin: 0 }` in `api/app/services/renderer/ir.py:9`.

**Why `body.scrollHeight` and not `documentElement.scrollHeight`:** the html element fills the iframe viewport, so once the iframe is grown to e.g. 5439px the html's scrollHeight reports 5439, locking the measurement in a positive feedback loop. The body's `scrollHeight` reports the natural content height regardless of the iframe's own size.

**No backend, no IR, no customizations, no test changes.** The overlay lives in the React tree as siblings of the iframe, not in the rendered HTML the backend produces, so Playwright's `prefer_css_page_size: true` never sees it.

## Implementation

- `web/src/components/preview/UserTemplateRenderer.tsx`:
  - Added `const PAGE_HEIGHT_PX = 1122` at module scope.
  - Added `const [iframeHeight, setIframeHeight] = useState<number>(PAGE_HEIGHT_PX)`.
  - Rewrote the second `useEffect` (line 60-80) to write the html, then on `requestAnimationFrame` read `iframeDoc.body.scrollHeight` and `setIframeHeight(h)`.
  - Replaced the wrapper `<div className="mx-auto max-w-[210mm] rounded bg-white shadow-sm">` with `<div className="relative mx-auto max-w-[210mm] rounded bg-white shadow-sm">`.
  - Removed the `h-[297mm] w-full` class from the iframe and bound the height via `style={{ height: \`${iframeHeight}px\` }}`.
  - Rendered `{breakRules.map((n) => <div ... />)}` below the iframe, where `breakRules = Array.from({ length: pages - 1 }, (_, i) => i + 1)` and `pages = Math.ceil(iframeHeight / PAGE_HEIGHT_PX)`.

## Verification

- **TypeScript build**: `cd web && npx tsc -b --pretty false && npm run build` — both clean.
- **Vitest**: `cd web && npx vitest run` — `1942 passed | 2 failed | 1 todo` (178 files). The 2 failures in `TemplateSwitcher.test.tsx` (Classic and Minimal template renders) are pre-existing JSDOM/iframe limitations and reproduce on the unmodified `master` branch (confirmed by `git stash` + re-run).
- **End-to-end smoke (browser)**: registered a new user, created a CV with the Classic template, added a long Experience description. With content height 5439px (5 pages), 4 rules appeared at 1122, 2244, 3366, 4488 px with labels "Page 2 starts" through "Page 5 starts". Assertion `document.querySelectorAll('div[aria-hidden="true"].pointer-events-none').length === pages - 1` held (3 === 4-1 for a 4-page state, 4 === 5-1 for a 5-page state).
- **PDF isolation**: exported the multi-page CV. PDF was generated successfully. `strings ~/Downloads/Smoke_CV.pdf | grep -iE "page|break|starts"` returned only `/Page` structural markers — no "Page 2 starts" or "rose" or "break" text. Overlay is preview-only.
- **Scroll behavior**: scrolling inside the preview column scrolls both the iframe and the rules (they share the same `relative` wrapper), so the rules stay aligned to the page boundaries.

## Follow-up

- None. The plan's "always-on, no toggle" call is locked in; if a future request needs a toggle, the rule list and the iframe-height state already gate cleanly behind a `showPageBreaks` boolean with no re-architecture.
- If the project ever supports non-A4 page sizes, `PAGE_HEIGHT_PX` moves to a prop driven by the template manifest. For now A4 is the only size (`pdf.py:61` hard-codes `format="A4"`).

<!-- Migrated from FEAT-01KZ4E8JCYRND8DVTHPJP2D80S during the schema-4 cutover. -->
