# Professional CV implementation evidence

Reviewed implementation: `02f4fd6`, 2026-10-07. All content is synthetic.
Plan: [implementation checkpoints](../../plans/2026-10-07-cv-professional-fixes.md).

`pdf-measurements.json` records actual production Chromium PDFs for all three
templates. Short content comes from `readability_sections()` in
`api/tests/test_pdf_readability.py`; long content comes from `_long_sections()`
in `api/tests/test_page_margin_geometry.py` (12 roles with five indexed bullets
each). It records per-page selectable glyph bounds, representative font sizes,
and local pdfplumber/PDFium recovery probes.

| Template | Short / long pages | Body / heading / name | Default text side inset |
| --- | --- | --- | --- |
| Classic | 1 / 3 | 10.5 / 12 / 18 pt | Approximately 36 pt |
| Minimal | 1 / 3 | 10.5 / 12 / 18 pt | Approximately 36 pt |
| Modern | 1 / 5 | 9 / 12 / wrapped 18 pt | Approximately 30 pt |

Physical top/bottom print margins are 36 pt on every page. Existing zone
padding remains authoritative, so first-page text can start farther down and
custom tighter padding can reduce the side inset. The rightmost Classic and
Minimal glyph inset is 35.46 pt, within the tests' 0.6 pt raster/geometry
tolerance. These page counts are observations, not targets or page limits.

Modern retains its existing two-zone content-box flex sizing. Applying
border-box to both zones initially narrowed the sidebar enough to break
LinkedIn recovery; limiting it to single-zone layouts restored all four
existing recovery cases. The report's Modern exact-name probe is false
because the name wraps and column text interleaves in extraction. Its empty
whole-phrase font probe does not mean missing name glyphs; existing PDF tests
measure the individual words. This preserves the known limitation of a
multi-column template rather than claiming full reading-order recovery.

`preview-measurements.json` and `mobile-measurements.json` record the actual
React preview using production Python HTML/PDF. Their input is the committed
short/long fixture in `../minimal-readability/preview-sections.json`, plus a
deliberately oversized entry and a saved `comfortable` zone padding case.
Ordinary short/long/saved-padding counts and page-two starts agree with PDF.
The oversized stress case is five preview pages and six PDF pages: Chromium
fragments inside the entry, and the preview exposes a named advisory without
blocking export. Mobile at 390 px has no horizontal overflow. The body
ResizeObserver settles after one callback per case.

Reproduce the executable regressions:

```bash
cd api
.venv/bin/pytest -q tests/test_pdf_readability.py tests/test_page_margin_geometry.py tests/test_minimal_readability.py tests/test_profile_urls_prompts.py
cd ../web
node scripts/test-preview-pagination.mjs
node scripts/test-profile-links-prompts.mjs
node --experimental-strip-types --test src/shared/cv/date.test.ts
```

The browser scripts require local Chromium execution permissions. Temporary
PDF/HTML/capture paths in the measurements are evidence from the recorded run;
the scripts regenerate fresh artifacts. Profile browser checks cover Space
key toggles, save/serialization/remount, both viewports, and new writing prompts.
API checks cover opt-in text and URI recovery, save/reload, read without
mutation, and owner preference/review freshness during tailoring.

The [independent integration review](integration-review.md) documents the
compatibility decisions. After that review, the final frozen backend suite
passed **978 tests with one skip**, and the release smoke gate passed. Full
frontend lint/typecheck, architecture fixtures/check, codegen check, three
tailoring tests, the date unit test, and browser fixtures passed. The existing
RichTextToolbar dependency lint warning remains. Logs are under
`/tmp/cv-professional-final-{pytest,smoke}.log`.

External ATS vendors were not tested directly.
