# CV builder and ATS audit — 2026-10-07

Audited revision `b8e4016`. The audit covers the editing surface, Python AST
builders, three system templates, canonical HTML/PDF export, and deterministic
ATS guidance. Product behavior and contracts were not changed.

**Recommendation:** retain Minimal as the default and improve its typography
and spacing; retain Classic as a serif alternative; offer a single-column
version of Modern for applications. Put a document compatibility check in
every builder and expand the existing scanner rather than adding a renderer
or a universal ATS score.

## Evidence and limits

- Generated six real Chromium PDFs through the production rendering pipeline:
  each system template with a short CV containing two jobs and a longer CV
  containing nine jobs. Both contain contact details, a summary, education,
  skills, a project, dates, bullets, and three web links.
- Used synthetic candidate content only. Inspected the three short PDF page
  images, physical page bounds, actual font sizes, pdfplumber and PDFium text,
  and the existing PDF recovery analysis.
- Ran pure reproductions for date presets, profile controls, hidden headings,
  and a compound job title. Ran 155 focused backend tests; all passed.
- Ran the Impeccable detector on the builder, section editors, and create-CV
  modal; it reported one width-transition warning. Shared UI was also inspected
  manually. The detector does not replace accessibility review.
- Reviewed official vendor guidance linked below. No PDF was submitted to a
  live Greenhouse, Workday, Lever, iCIMS, or other ATS account. Local extraction
  is evidence about Aergia's output, not proof of a vendor's parsing behavior.
- The application UI review is based on source. There was no authenticated
  desktop/mobile interaction or measured UI contrast audit. Synthetic fixtures
  lean toward software roles; broader career and language coverage is needed.

Generated evidence is summarized in
[`cv-builder-ats-audit-2026-10-07-results.json`](cv-builder-ats-audit-2026-10-07-results.json).
The PDFs, PNGs, HTML, raw extraction text, complete scanner results, and audit
runner are in `/tmp/aergia-ats-audit/` and `/tmp/aergia-ats-audit.py` for this
workspace session. These temporary files contain no real candidate data.

## What already works

The AST → resolver → HTML → Chromium path is shared by preview and export.
That is the right foundation for consistent changes. Experience and education
have separate fields for identity and dates. Project, certification, and
research metadata render before descriptions, and default web-link labels
retain usable hostnames and paths. Skills already render as comma-separated
category lists; replacing them is unnecessary. Rich text exports semantic
paragraphs and lists. Ordinary export saves before downloading. Tailored drafts
already track review freshness and allow explicit reevaluation.

The scanner separates semantic fit, literal wording, document recovery, and
writing quality. It already checks rendered text, contacts, entry dates, links,
and agreement between two local parsers. Preserve those distinctions and the
evidence requirements for wording recommendations.

## Template test results

The short and long fixtures used the same content across templates. No
characters exceeded the physical page width. Files were approximately
34–46 KB. All six recovered email and phone, entry anchors, date associations,
and clickable links.

| Template | Short / long pages | Heading recovery | Visible web addresses | Parser agreement | Assessment |
| --- | --- | --- | --- | --- | --- |
| Modern | 1 / 3 | 3/4 in both | 2/3 in both | Warning in both | Sidebar introduces observed extraction problems |
| Classic | 1 / 2 | 4/4 in both | 3/3 in both | Pass in both | Strong structural baseline; body text is small |
| Minimal | 1 / 2 | 4/4 in both | 3/3 in both | Pass in both | Strong structural baseline; spacing is too compressed |

The primary extractor begins Modern with:

```text
Alexandra Experience
Senior Software Engineer 0 January 2025 – Present
Bennett
Northstar Systems 0 Halifax, NS
Senior Software Engineer
```

The sidebar summary also interrupts job bullets. PDFium reads the complete
sidebar before the main column. Both layouts look readable to a person, but
the two extractors produce materially different content sequences. Modern's
longer LinkedIn slug wraps at a hyphen and fails visible-address recovery in
the primary extractor. No text clipping was observed; extraction order is the
problem. This is consistent with the previously documented sidebar limitation
in `BUG-01M3HTTAWH8Y9AWSYA8AVRPY3R`, rather than evidence that the recent project
metadata fix regressed.

## Findings

Found **12 findings: 3 P1 and 9 P2**. P1 means a significant output or editing
accessibility problem; P2 means an improvement, bounded defect, or missing
guidance. Features proposed here are not implemented fixes. No P0 was found.

### A01 — P1: Modern's sidebar breaks a reliable reading sequence

**Evidence:** the PDF extraction above; `api/app/db/seed.py:35` places profile
in the sidebar and all other sections in the main zone. The document renderer
puts those zones beside one another at
`api/app/services/renderer/html_renderer/html_document.py:186`.

**Impact:** a parser can confuse identity, summary, and employment text.
Greenhouse documents column layouts as a potential parsing problem; this is
also an observed local problem, without asserting that every ATS fails it.

**Recommendation:** add a versioned single-column Modern template with the
profile at the top. Keep the existing layout available with a specific
compatibility explanation. Warn on resolved multi-zone side-by-side layouts,
including custom layouts. Describe risk rather than labeling a template
universally certified. Offer an explicit layout conversion, preserving content
and user style choices unless the user chooses to reset them.

### A02 — P1: A passing reading-order check misses identity/body interleaving

**Evidence:** Modern's `reading_order` passes at 7/7 short and 14/14 long,
despite the scrambled sequence. `api/app/scanner/pdf_recovery.py:926` measures
the order of section and entry anchors; the profile name and summary are not
part of the same structural sequence. The separate parser-agreement check
correctly warns, so the overall analysis is not wholly passing.

**Recommendation:** retain the anchor check but describe its scope clearly.
Add name/contact block association and entry body continuity checks using
resolved field provenance and bounded PDF geometry. Treat parser disagreement
as actionable diagnostic evidence. Cover a wrapped full name and sidebar
summary alongside multi-entry work history. Never convert a local pass into an
ATS success probability.

### A03 — P1: Core editing actions lack keyboard and accessible form support

**Evidence:** `web/src/shared/ui/AccordionPanel.tsx:31` uses a clickable div
without keyboard behavior or expanded-state semantics. Section and entry
reordering register only PointerSensor in
`web/src/features/builder/components/ContentSectionList.tsx:48` and
`web/src/shared/ui/SortableAccordionList.tsx:112`. Profile and experience text
labels are visually adjacent but have no `htmlFor`/input ID association;
social fields rely on placeholders, and the icon select has no accessible name.

**Recommendation:** use a real accordion toggle button with `aria-expanded`
and `aria-controls`, separate from sibling actions. Add keyboard sorting and
Move up/down actions, contextual drag-handle names, and associated field
labels. These address WCAG 2.1.1, 1.3.1, 3.3.2, and 4.1.2 concerns. Verify
keyboard-only completion and accessible names in the actual app.

### A04 — P2: Compatibility analysis is not available for every builder

**Evidence:** `BuilderHeader.tsx` offers scanner access through application or
pending-draft context. `useBuilderApplicationContext.ts` treats a CV without
that context as ordinary. `ExportPDFButton.tsx:24` saves and downloads without
offering a document check. A user writing a general CV cannot use the same
document checks directly from that flow.

**Recommendation:** add “Check document” independently of a job description.
Reuse PDF recovery and rendered structure checks; semantic job fit remains
optional. Provide plain recovered text and a structured view of name,
contacts, roles, organizations, dates, headings, and links. Show findings with
links to the affected section/entry. Bind results to the exact saved content,
template, customizations, and PDF; edited content must mark results stale.
Offer checks during export without making advisory findings a download gate.

### A05 — P2: Fourteen platform entries contain no platform-specific evidence

**Evidence:** `api/app/scanner/ats_guidance.py:608` has an empty `ATS_SOURCES`
registry. Platform entries at line 725 are emitted with empty findings, tips,
and source IDs, while `platforms_checked` reports 14. The UI at
`ScannerAnalysisDrawer.tsx:388` does explain that core checks apply, but
fourteen empty disclosures add noise and imply more coverage than exists.

**Recommendation:** populate sourced deltas first for Greenhouse and Workable:
their published layout/section advice and file limits are concrete. Store the
source, reviewed date, scope, and confidence. Show only meaningful platform
guidance, and distinguish “common checks available” from “vendor guidance
reviewed.” Use the existing registry and freshness mechanism. Do not invent
Workday, Lever, iCIMS, or Taleo parsing rules when accessible evidence is absent.

### A06 — P2: Template defaults favor density over readability

**Evidence:** all six PDFs have 9 pt descriptions, dates, contacts, links,
and skill tags, from `html_document.py:115`. Minimal sets spacing to `none`
at `seed.py:145`, producing no inherited section or entry gap. The inspected
PDF crowds the education, skills, and project boundaries. Modern inherits the
blue accent as the color of whole sections through
`resolution/sections.py:43` and `html_sections.py:76`; its body is blue too.

**Recommendation:** introduce a readable default around 10.5–11 pt for body
text, modest entry gaps, and stronger section spacing; reserve compact density
as an explicit choice. These sizes are design recommendations, not vendor
thresholds. Use neutral body text and accent headings/dividers. Permit two
pages when the evidence warrants it. Calibrate field hierarchy so increasing
body size does not flatten the candidate name to the same size as metadata.
Use a deterministic available font stack or local font assets; declared Inter
and Crimson currently depend on environment fallback.

### A07 — P2: Date presets conflict with the scanner's own conventions

**Evidence:** `builders/_utils.py:79` provides separators that produce strings
such as `01/2022/06/2024` and `Jan-2022-Jun-2024`. In a reproduction, seven
of ten finished-date-range presets were marked nonstandard. Even the clear
`2022-01 – 2024-06` fails `_CONVENTIONAL_DATE_RE` at
`scanner/ats_guidance.py:199`. The normal Month YYYY default passes.

**Recommendation:** prefer `Jan 2022 – Jun 2024` or the existing full-month
default. Use an unambiguous range separator independently of the date's
internal punctuation. Recognize clear ISO/numeric ranges correctly. Preserve
stored preferences and distinguish a supported unusual style from evidence
of actual recovery failure. Test all presets for completed and current roles,
single certification dates, and missing endpoints. Backend chronology checks
should be advisory where incomplete historical data is legitimate.

### A08 — P2: Hidden headings and absent identity are not equivalent to recovery success

**Evidence:** `_resolved_facts()` includes only headings intended for display,
and `_heading_findings()` only checks that collection. Hiding Experience
therefore returns no heading-convention finding. Contact recovery checks
contacts supplied to it; it does not require a name or contact method.
`_ENTRY_FIELDS` has no profile completeness rule.

**Recommendation:** keep recovery comparisons limited to rendered content,
then separately check semantic readiness: name, at least one preferred contact
method, and recognizable headings for populated work/education/skills sections.
Allow Profile to remain untitled. Warn about missing or suppressed headings
without claiming the parser failed to recover text that was intentionally
hidden. Do not require a phone number, full street address, or personal photo.

### A09 — P2: A valid compound job title is classified as multiple roles

**Evidence:** `_entry_findings()` at `ats_guidance.py:270` matches spaced
`and`, `&`, or `/` in a title. “Research and Development Engineer” with company
and dates is reported ambiguous, with advice to split the role.

**Recommendation:** require stronger evidence of combined jobs and exempt
common compound titles. Use an advisory review question when uncertain. A
single actual job should not be split to satisfy a keyword heuristic. Preserve
official role names; an accurate parenthetical expansion can improve clarity
without changing employment history or inventing seniority.

### A10 — P2: Profile controls advertise output that is not implemented

**Evidence:** `ProfileEditor.tsx:53` exposes email clickability and line 178
exposes Photo URL. `builders/profile.py:23` emits plain email text and never
reads either setting. Rendering otherwise identical profiles with the toggle
on/off produces identical HTML; neither `mailto:` nor the supplied photo URL
appears in output.

**Recommendation:** implement the email-link choice without hiding its
address. Remove or explain unsupported photo input after a deliberate product
decision; adding photos is unnecessary for the recommended application layout.
Audit customization controls against RendererSupport too: `skill_variant` is
retained for compatibility but intentionally ignored by the HTML skill path.
Remove no stored fields merely as an incidental cleanup.

### A11 — P2: Custom link labels can hide useful destination information

**Evidence:** default fallback labels are good, but `site_text`, social labels,
and entry `link_text` are preserved verbatim. The profile editor even suggests
“Personal Site.” A PDF may therefore print only “LinkedIn” or “Portfolio” while
retaining the actual address solely as an annotation. The existing scanner
already identifies this distinction.

**Recommendation:** offer a short visible address by default, with an explicit
custom-label option and an example of text extraction. Preserve authored
labels. Explain findings as a text-reader/recovery concern rather than saying
every ATS requires clickable links. Let people supply stable short URLs;
never truncate paths or invent redirects. Avoid arbitrary wraps inside email
and URL identities where a separate contact line would fit them better.

### A12 — P2: Page format and tailoring assistance can be more useful

**Evidence:** `html_values.py:143` and `_pdf_runtime.py:105` fix export to A4;
preview geometry is also explicitly A4. General editors offer free-form
descriptions, but builder content editing is separate from job-evidence
inspection. The small fixture fits on one page while leaving substantial
unused vertical space; reducing type further is unnecessary.

**Recommendation:** support Letter and A4 through one shared page specification
used by server rendering and preview pagination. Provide career-sensitive
starting structures for experienced candidates, graduates, career changes,
and research CVs. Surface existing supported/partial/missing job evidence
beside editing with jump-to-entry actions. Suggest wording only when backed by
candidate evidence. Offer action/context/outcome prompts and achievements
without demanding a number for every statement. Preserve strong evidence
instead of enforcing a universal one-page rule.

## Source-based interface assessment

Implementation integrity is **partially passing**: feature ownership, the
single renderer, tokens, save handling, and review freshness form a coherent
product. Dead controls and inaccessible editing actions are substantive gaps.
The following is a provisional source-review score, not a measured WCAG or
performance certification.

| Dimension | Score / 4 | Evidence |
| --- | --- | --- |
| Accessibility | 1 | Accordion toggle, pointer-only sorting, and unassociated labels |
| Performance | 3 | Debounced, rate-limited preview with cancellation; small width-transition issue |
| Responsive design | 2 | Desktop/mobile layout exists, but mobile splits editing and preview into half-height panes; small controls need interaction testing |
| Theming | 3 | App tokens are widely used; renderer chips and accent/body coupling limit consistency |
| Implementation integrity | 2 | Coherent architecture with dead controls and weak readiness diagnostics |
| Total | 11/20 | Significant targeted work; no evidence that a full redesign is needed |

The detector's `TokenPicker.tsx:80` width transition is a low-impact visual
indicator, not demonstrated application-wide layout thrashing. Treat it as
P3 polish, separate from the 12 principal findings. A manual shared-UI read
also finds height animations; verify reduced-motion behavior in the actual
app before claiming an accessibility failure from animation alone.

## Implementation order and acceptance checks

| Phase | Work | Acceptance evidence |
| --- | --- | --- |
| 1 | Single-column Modern option; improve Minimal/Classic defaults; fix date/title false positives and dead profile controls | Recommended application templates recover identity, headings, entries, dates, and visible addresses across both parsers; retained sidebar variants report their risks; readable body sizes; intentional settings affect output |
| 2 | Document check for all CVs; stronger association checks; direct links to fields; keyboard and label fixes | Standalone CV can be checked without a job; results are bound to the rendered revision and become stale on edit; keyboard-only user can open, edit, reorder, and export |
| 3 | Sourced platform deltas; Letter/A4; contextual job evidence and career-sensitive structure | Vendor claims carry current citations; page size agrees between preview and PDF; supported wording recommendations retain provenance |
| Later | Consider DOCX/plain-text export when actual application requirements justify it | Preserve the canonical AST/resolved semantics; no React screenshot export or ad hoc second document model |

PDF already works as a supported upload format in the vendor sources below;
DOCX is an additional capability, not an urgent universal fix. If introduced,
it needs a deliberate export architecture consistent with the repository's
HTML-first path and its own parity/recovery tests.

Extend the existing `test_pdf_readability.py` rather than starting a parallel
test harness. Add long names, longer LinkedIn slugs, international characters,
long employers/titles, repeated dates, missing contact fields, hidden headings,
page-boundary jobs, certification/research records, languages, and custom
styles. Include business, operations, clinical, and academic content. Test
field association, not only token retention. Keep synthetic fixtures realistic
when running authorized vendor parsing trials, and record both correctly
populated and incorrectly associated fields. Never send candidate data to a
third-party scanner without authorization.

For future changes, run focused tests while iterating, generated-schema checks
after model changes, frontend structure checks, tracker validation, and the
repository smoke gate for release. The audit itself changed documentation
only, so a full release smoke run was not necessary.

## Vendor sources reviewed

- [Greenhouse: Unsuccessful resume parse](https://support.greenhouse.io/hc/en-us/articles/200989175-Unsuccessful-resume-parse),
  updated March 2, 2026: lists columns, complex tables/headers/footers, contact
  details in header/footer/text boxes, graphics, unclear sections, and incomplete
  job titles as potential problems. Its parsing limit is 2.5 MB. Do not append
  invented legal suffixes to employers just because its advice mentions them.
- [Workable: Import your resume details to autofill the application](https://jobseekers.workable.com/hc/en-us/articles/360036231313-Import-your-resume-details-to-autofill-the-application),
  updated September 30, 2026: accepts PDF, DOC, DOCX, ODT, and RTF up to 5 MB;
  recommends clear sections/readable fonts and avoiding image-only resumes.
- [SAP SuccessFactors: Candidate Profile](https://help.sap.com/docs/successfactors-recruiting/setting-up-and-maintaining-sap-successfactors-recruiting/candidate-profile-in-sap-successfactors):
  documents PDF and DOCX among accepted attachment types and disallows protected
  PDFs. Attachment acceptance alone does not prove parsing accuracy.
- [Oracle Taleo: Attachment](https://docs.oracle.com/en/cloud/saas/taleo-enterprise/24d/otrcg/c-attachment.html):
  documents PDF and Word among attachment formats. This is release-scoped
  attachment guidance, not a current universal Taleo parser specification.

Lever's resume-parsing help page did not expose usable article content during
this audit. No specific Lever claim is inferred from that failure. Workday and
iCIMS were not tested. Treat vendor names as review targets until evidence
supports an actual rule.
