# Minimal readability PDF evidence

`baseline.json` records the pre-change PDF measurements from the synthetic
audit run at revision `b8e4016`. The run used the production render pipeline
and Playwright singleton for Classic, Modern, and Minimal, with short and long
fixtures. It includes page counts, physical page bounds, and PDF character
sizes and boxes for representative identity, heading, date, body, URL, skill,
and project text.

The short PDFs are A4 (`594.96 × 841.92 pt`) and have no characters outside
the physical page bounds. All three templates render an 18 pt candidate name
and 12 pt section and project headings. Representative descriptions, dates,
email, and skill text are 9 pt; the visible LinkedIn address measures 9.96 pt
in Classic and Minimal. Modern places the profile on the left (`x=41.86 pt`)
and its Experience heading in the main column (`x=210.66 pt`), while Classic
and Minimal place the Experience heading at `x=24 pt`.

The long audit fixture occupied two pages in Classic and Minimal and three in
Modern. The short fixture occupied one page in each. These are recorded
observations, not page-count requirements. The Modern audit already found
sidebar reading-order and address-recovery warnings; this baseline keeps those
known limitations visible.

PDF, PNG, HTML, and parser text artifacts remain under `/tmp/aergia-ats-audit/`
and contain synthetic content only. The baseline report includes their paths.
No old preview PDF or stored scan result was rewritten.

## Post-change render evidence

`current-results.json` records the reviewed renderer output under
`/tmp/minimal-current-audit/`. The short and long Minimal fixtures use 10.5 pt
body text with 18 pt names and 12 pt headings; they occupy one and two pages,
with no characters outside the physical page. All local recovery checks pass
for Minimal and Classic. Modern retains its existing section-heading,
visible-address, and parser-agreement warnings.

The four Classic and Modern short/long PNGs have byte-identical SHA-256 values
to the pre-change images. The HTML path for each result is the rendered
preview source used to create its paired PDF, so P04 can compare those exact
artifacts. The long Minimal PDF, HTML, PNG, pdfplumber text, and PDFium text
are listed individually in `current-results.json`.

## Reproduce preview/export pagination

`preview-sections.json` contains the original synthetic short/long audit
content. After installing the repository's API and web dependencies, run:

```bash
cd web
node scripts/test-minimal-inheritance.mjs
node scripts/test-preview-pagination.mjs
```

The pagination fixture generates fresh HTML and PDF through the production
renderer, mounts `UserTemplateRenderer`, and checks its typography, spacing,
page counts, intact entries, and page-two starting entry against PDF export.
It writes screenshots and measurements under `/tmp/minimal-preview-*`.
Chromium requires the normal local-browser execution permissions.

The [independent integration review](review.md) records the discovered and
corrected preview measurement defect and the remaining coverage limitation.
