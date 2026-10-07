# CV templates compared with professional resume conventions

Reviewed: 2026-10-07. Product revision: `65368f4` on `master`.
Scope: Classic (interpreting “usual CV”), Minimal, and Modern as a secondary
comparison. This is a document-output audit, not a redesign of the builder.

**Conclusion:** Minimal is a good general application baseline after the recent
readability fixes. Classic needs comparable body typography and entry spacing.
Both would benefit from consistent physical page margins. Date presets and
custom URL labels have narrower, reproducible improvements available.

## Comparison method

Two independent GPT-6 Luna assessments at max reasoning reviewed visual design
and technical PDF output. The visual assessment finished before the technical
detector findings entered synthesis. Both inspected current production HTML,
PDF, and PNG artifacts; the technical review also measured later pages and
font embedding. The coordinator checked source paths and reproduced date
presets and custom-label PDF extraction through the production pipeline.

The baseline includes synthetic short and long documents, not a personal CV.
These artifacts match the current renderer/defaults and are described in
[the committed evidence](fixtures/minimal-readability/README.md). The long
fixture repeats nine numbered jobs and similar bullets to stress pagination;
its page balance is an observation, not a rule for every real candidate.

There is no universal industry or ATS-certified CV design. I compared against
[Harvard's 2026 resume samples](https://cdn-careerservices.fas.harvard.edu/wp-content/uploads/sites/161/2026/02/HES-Resume-samples-combined.pdf),
[MIT's sample resumes](https://cdn.uconnectlabs.com/wp-content/uploads/sites/123/2021/08/sampe-resumes-capd.pdf),
and primary career-service and employer guidance. The samples demonstrate
different legitimate choices; their layouts are not all equally suitable
for every parser or career stage.

## Current output

| Property | Classic | Minimal | Comparison |
| --- | --- | --- | --- |
| Main layout | Single column | Single column | Familiar structure for broad applications |
| Body, dates, contact text | 9 pt | 10.5 pt | Classic needs a legibility improvement |
| Name / section headings | 18 / 12 pt | 18 / 12 pt | Clear hierarchy worth retaining |
| Body line height | Browser default | 1.4 | Minimal has a predictable reading rhythm |
| Section / entry / field defaults | 20 / 0 / 0 px | 16 / 8 / 4 px | Classic groups unrelated entries too tightly |
| Horizontal text inset | About 24 pt (0.33 in) | About 24 pt (0.33 in) | Narrower than common resume guidance |
| Short / long fixture pages | 1 / 2 | 1 / 2 | Page count alone does not show page balance |
| Existing local recovery checks | All ten pass | All ten pass | No demonstrated regression in ordinary extraction |
| PDF fonts | Embedded Liberation Serif subset | Embedded Noto Sans subset | Text is real and selectable |

## Recommended improvements

### C01 — High: bring Classic up to readable defaults

Classic omits `body_font_size` and `body_line_height` in
`api/app/db/seed.py:110`; descriptions, contacts, dates, and URLs therefore
use the shared 9 pt fallback in
`api/app/services/renderer/html_renderer/html_document.py:124`.
The measured PDF agrees with the source. Minimal's 10.5 pt body is visibly
easier to read. MIT recommends at least 10 pt for resumes.
[MIT resume guidance](https://capd.mit.edu/resources/resumes/)

Use the existing `small` size and `normal` line-height tokens for Classic,
retaining its serif identity, 18 pt name, and 12 pt headings. Add modest entry
and field gaps through the existing `snug` and `tight` defaults. Leave explicit
authored styles effective and keep a compact option available.

Classic's long fixture currently leaves only Skills and Projects on page two,
occupying approximately 13% of that page vertically. Minimal's page-two text
spans approximately 78%. Larger Classic type and better entry rhythm should
improve the distribution, but must be checked with varied, realistic content.
Do not stretch content to fill a page or shrink text to meet a page limit.

### C02 — High: use consistent page margins, including later pages

The print rule in `api/app/services/renderer/html_values.py:102` is
`@page { size: A4; margin: 24px 0 0 0; }`. The templates supply a 32 px
zone padding instead of physical side/bottom margins.

Measured first-page text starts roughly 44–49 pt below the top, but page-two
text starts only 19–22 pt below the top. Horizontal text bounds are roughly
24 pt from the sides; Classic's long first-page text ends about 28 pt above
the bottom. Zone padding does not establish equal repeating page margins.
Berkeley recommends 0.5–1 inch margins around resumes, with 10–11 pt text.
[Berkeley resume guidance](https://www.career.berkeley.edu/prepare-for-success/resumes/)

Target an effective text inset of at least 36 pt (0.5 in), and use a physical
top/bottom margin that repeats on every page. Account for existing zone
padding so the two are not accidentally added twice. A small set of document
margin presets would be more useful than requiring section-by-section edits.

This change must update preview geometry and the paginator alongside PDF
geometry (`web/src/features/builder/components/preview/pageGeometry.ts:13`).
Preserve saved layout overrides: CV creation copies template zones into the
document, so changing only a seed's padding would not update existing CVs
consistently. More generous margins can increase page counts legitimately.
This is a readability recommendation, not an ATS rejection threshold.

### C03 — Medium: keep date ranges unambiguous

The normal full-month default is clear and consistent. The shorter
`Mon YYYY` option also works well and leaves more space beside long titles.
Some other presets use their internal punctuation as the range separator.
Through the actual resolver pipeline, the completed-job examples are:

| Preset | Current output |
| --- | --- |
| Month YYYY | `January 2024 – December 2024` |
| Mon YYYY | `Jan 2024 – Dec 2024` |
| MM/YYYY | `01/2024/12/2024` |
| Mon-YYYY | `Jan-2024-Dec-2024` |

Use a spaced en dash between endpoints regardless of punctuation inside each
date. Prefer clear month/year formats in the controls, retain explicit saved
preferences, and make scanner guidance recognize supported clear numeric
formats. Source: `api/app/services/renderer/builders/_utils.py:66` and
`web/src/features/builder/components/customization/groups/LayoutGroups.tsx`.
This is the still-open date issue identified in the
[earlier audit, A07](cv-builder-ats-audit-2026-10-07.md).

### C04 — Medium: offer visible URLs alongside custom labels

The profile editor accepts labels such as “Personal Site” and “LinkedIn.”
`api/app/services/renderer/builders/profile.py:30` emits the label as visible
text and keeps the destination in the PDF link annotation.

A new synthetic production PDF confirmed that both pdfplumber and PDFium
recover those labels, but neither text output contains the portfolio or
LinkedIn address. The link annotations still contain the complete URLs.
This is a destination-visibility limitation, not a broken clickable link.

Offer “show URL beside label,” or explain the tradeoff when editing a label.
Use a readable domain/path and preserve the full clickable destination. Do
not silently replace authored labels. Roche recommends visible URLs and warns
that hyperlink text can be handled differently by parsers.
[Roche resume-parsing guidance](https://careers.roche.com/global/en/resume-parsing-faq)

### C05 — Medium: help users write and organize the right evidence

The experience editor currently offers a generic summary/bullet placeholder
(`web/src/shared/cv-editor/section-editors/experience/ExperienceEditor.tsx:65`).
Add optional prompts for action, scope, and result; suggest a metric only when
the candidate has supporting evidence. Use gentle length guidance for the
profile summary and bullets, rather than hard limits or invented results.
Harvard emphasizes concise, specific, factual writing and ordering relevant
sections by importance.
[Harvard resume guidance](https://careerservices.fas.harvard.edu/resources/create-a-strong-resume/)

Section and entry reordering already exist. Improve starting presets for
graduates and experienced applicants instead of rebuilding those controls.
Do not automatically move Education first for every user or sort incomplete
historical dates without consent.

### C06 — Medium: explain oversized entries before export

Ordinary entries stay together, and the recent preview correction is working.
An entry taller than a printable page can still split despite Chromium's
`break-inside: avoid`. That limitation is acknowledged by
`api/app/document_schema/models.py:228`.

Show a small advisory at an affected entry when measured height exceeds a
printable page. Suggest shortening or splitting the description; keep export
available. Reuse the existing preview measurements and report genuine overflow
separately from an ordinary two-page CV. Avoid auto-shrinking text.

## Optional polish and larger additions

- Plain or neutral project technology labels would give Minimal a more uniform
  monochrome look. The current blue pills contain selectable text and are not
  a demonstrated ATS failure; treat this as an aesthetic choice.
- US Letter could be a regional page-size option; A4 is currently fixed in
  both export and preview. This would require synchronized page geometry.
- PDF title metadata and tagged output would improve organization and
  accessibility. Current PDFs have embedded fonts but no title/author and are
  untagged. There is no evidence that the missing metadata blocks extraction.
- Consider DOCX export only as a separately scoped feature where target
  application instructions require it; the appropriate format is employer-
  specific, and the current PDF path should remain intact.
- If academic users are a target, offer a separate academic starting structure
  for publications, teaching, presentations, grants, and service. Generic Extras
  can already hold this information, but structured guidance would help.
  Academic CVs follow different discipline and length conventions.
  [Harvard academic CV guidance](https://careerservices.fas.harvard.edu/resources/gsas-cv-cover-letter-guide-2/)

## What to retain

Keep Minimal's current typography hierarchy, single-column body, visible
conventional headings, selectable bullet text, comma-separated skills, clear
role/employer/date association, optional GPA, and URL wrapping. Classic also
has a sound underlying structure. Both ordinary fixtures pass local recovery
checks for text, contacts, headings, entries, dates, links, and parser agreement.

Modern remains an expressive secondary option. Its long fixture is three
pages, with Projects alone on page three, and its existing sidebar recovery
warnings remain relevant. Greenhouse explicitly lists columns and complex
tables/header/footer arrangements among parsing risks. This supports keeping
a single-column application option prominent; it does not establish a
universal ban or a guaranteed result for any vendor.
[Greenhouse parsing guidance](https://support.greenhouse.io/hc/en-us/articles/200989175-Unsuccessful-resume-parse)

## Suggested execution order

1. Add Classic typography and modest entry/field gaps using existing tokens.
2. Implement shared page-margin geometry with preview/export regressions.
3. Fix date separators and the associated scanner-format inconsistency.
4. Add opt-in URL visibility and oversized-entry advice.
5. Improve content prompts and career-stage starting presets.

For each patch, preserve authored overrides and use synthetic short, long,
international, and deliberately oversized fixtures. Measure actual font sizes,
physical margins on each page, text and URI recovery, and the preview/export
page-two start. Do not promise one page or universal external ATS acceptance.

## Audit evidence and limits

Temporary handoffs: `/tmp/cv-visual-comparison.md` and
`/tmp/cv-output-comparison.md`. Extra visual page captures are under
`/tmp/cv-visual-pages/`. Benchmark PDFs and sample images are under
`/tmp/aergia-industry-{harvard,mit}*` and were used only for inspection.
The custom-label PDF and parser report are
`/tmp/cv-industry-custom-label.pdf` and
`/tmp/cv-industry-custom-label-results.json`.

One Impeccable detector pass over six saved HTML artifacts produced ten generic
font/spacing warnings (`/tmp/cv-output-detect.json`). Those are web-design
heuristics, not ATS findings: in particular, “overused Inter” is not evidence
that a resume needs a less common font, and repeated 4 px spacing does not
override direct measurements of the template's 16/8/4 px rhythm.

No product code, stored CV, template defaults, or deployment was changed by
this audit. No full test suite was rerun; focused reproductions and current
production artifacts support the findings. External ATS vendors were not
tested directly. Questions skipped: this was a comparison request, and no
user decision was needed to complete the audit.
