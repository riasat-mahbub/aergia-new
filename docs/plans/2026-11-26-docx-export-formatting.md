# Preserve CV formatting in DOCX exports

Apply a CV's resolved spacing, typography, colors, and alignment to its editable Word export. Use native Word paragraphs, runs, and styles in the single-column layout. A CV with larger entry gaps or different heading typography should show those choices in the downloaded file.

Implemented in `4a81dda`, `81a9604`, and `6d996c6`. The [tracker](../../tracker/features/FEAT-01M129QBNK54QF2Y9PV8WDKN8P-latex-docx-renderer-backends.md#docx-formatting) records the export and Office checks.

## Reproduction and scope

Export the same CV before and after changing global spacing, then change the Experience section's entry gap, field gap, alignment, and typography. In the reproduced case, HTML showed the new styles while `word/document.xml` and `word/styles.xml` stayed identical. The resolver carried the changed values. The Word renderer applied fixed Arial, single spacing, and generic paragraph gaps. A native Word fixture preserved the proposed formatting through edit, save, and reopen.

This pass covers paragraph rhythm, font and color choices, paragraph alignment, dividers, shading, and right-aligned fields. Browser template sidebars, zone backgrounds, and chip layouts can be handled separately as Word-specific layout work. PDF supplies the browser layout and exact pagination. [Current DOCX renderer](../../api/app/services/renderer/docx.py) · [Resolved styles](../../api/app/services/renderer/resolution/render_model.py)

## Implementation order

### 1. Apply the resolved spacing and typography

1. Extend `api/tests/test_docx_renderer.py` with an A/B fixture that renders identical text with different styles. Assert that a change in spacing changes the expected paragraph properties, and a change in typography changes the expected font properties.
2. Add a small formatting adapter inside the DOCX renderer. Read the existing resolved defaults for section, entry, and field spacing, body size and line height, and body and heading fonts. Use the existing token and palette maps for section and run overrides. Convert the resolver's known lengths to Word points in one place. Map known font tokens or stacks to a single Word font family. Missing values use the existing Word defaults. Keep token conversion separate from layout code and let the shared resolver own the cascade. [Renderer pipeline](../../api/app/services/renderer/pipeline.py)
3. Set Normal, Title, and Heading 1 defaults from the resolved document values where applicable. Apply section heading and body overrides to the corresponding paragraphs. Apply authored run color, size, and emphasis overrides to both plain and linked text. Preserve explicit false values for emphasis, hyperlink relationships, and the heading levels in Word's outline. [Word character and paragraph formatting](https://python-docx.readthedocs.io/en/latest/user/text.html)
4. Apply section before and after spacing to the first and last emitted paragraphs. Use entry gaps between entries and field gaps between field rows within the same entry. Preserve existing rich-text paragraph and list boundaries. Treat `none` as an explicit zero. Give each boundary one effective spacing value. When separate contributions should add, combine them on one side, since Word uses the greater of the adjacent before and after values. Skip missing or empty content without leaving a gap or adding blank paragraphs. [Word paragraph spacing](https://python-docx.readthedocs.io/en/latest/user/text.html#paragraph-spacing)

### 2. Map the editable layout details

1. Set native paragraph alignment from `SubsectionStyle.text_align`. Apply heading dividers with paragraph borders and section background colors with paragraph shading. Treat shading as a paragraph fill. Use the existing resolved section and accent colors for headings and dividers. Keep the WordprocessingML helpers small and check the emitted element order. [Word paragraph properties](https://learn.microsoft.com/en-us/office/open-xml/word/working-with-paragraphs)
2. Use `FieldBlock.align` to recognize rows with right-aligned dates or metadata. Place a short right-side value at a right-aligned tab stop computed from the usable page width. Stack the right-side value on its own right-aligned paragraph when the row has competing right fields, rich content, or insufficient space. Preserve field order, text, and links in both layouts. [Word tab stops](https://python-docx.readthedocs.io/en/latest/user/text.html#tab-stops)
3. Keep title and metadata paragraphs with the first body paragraph when the entry spans several paragraphs. Let the rest of a long entry flow across pages. Use the existing section break and heading-keep policy. Set renderer capabilities to reflect the behavior actually tested in Word. [Word pagination properties](https://python-docx.readthedocs.io/en/latest/user/text.html#pagination-properties)

## Acceptance checks

- **Spacing.** Verify Minimal's 8 px entry gap and 4 px field gap become 6 pt and 3 pt in the correct locations. Exercise a global spacing override, a local override over it, explicit zero, empty sections, hidden headings, and consecutive lists. Check that local Before and After affect section edges exactly once.
- **Typography.** Verify Minimal exports its 10.5 pt body size and 1.4 line spacing. Exercise document, section, and run precedence for font family, size, line spacing, and color. Include both plain and linked runs, a palette color, heading and body overrides in the same section, and legacy CVs with unset overrides.
- **Layout and content.** Verify section alignment, divider toggles, shading, a short tabbed date, and stacked fallback for a long title or rich metadata. Confirm the title, employer, date, and description remain associated and appear once. Exercise one built-in sidebar template to confirm its sections stay in source order in the Word document.
- **Office compatibility.** Generate short and multipage fixtures with real export calls. Open them in Microsoft Word and LibreOffice, edit and reopen a copy, and check spacing, tab alignment, heading placement, and long-entry page flow. Validate the package with the Open XML SDK and inspect the editable text, lists, and hyperlinks.
- **Regression checks.** Run focused DOCX renderer, export route, HTML renderer, and PDF tests, plus the release smoke gate. Compare HTML before and after for the same fixtures. The prior verification reports eight PDF font-size assertions that also failed on the pre-DOCX commit. Record any additional failures separately. [Tracker verification](../../tracker/features/FEAT-01M129QBNK54QF2Y9PV8WDKN8P-latex-docx-renderer-backends.md)
