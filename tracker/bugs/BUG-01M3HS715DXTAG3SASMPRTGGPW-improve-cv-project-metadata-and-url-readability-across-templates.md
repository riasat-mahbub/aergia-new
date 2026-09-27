---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3HS715DXTAG3SASMPRTGGPW
TYPE: bug
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - BUG-01M339P61TKT5MPVHPYXMRHT1X
  - BUG-01M2410BFKZBWF86V9WVRFPJRA
AFFECTS:
  files:
  - api/app/services/renderer/html_renderer/html_entries.py
  - api/app/services/renderer/html_renderer/html_fields.py
  - api/app/services/renderer/html_renderer/html_sections.py
  - api/app/services/renderer/builders/_utils.py
  - api/app/services/renderer/builders/profile.py
  - api/app/services/renderer/builders/projects.py
  - api/app/services/renderer/builders/research.py
  - api/app/services/renderer/builders/certifications.py
  - api/app/scanner/pdf_recovery.py
  - api/app/scanner/pdf_worker.py
  - api/app/scanner/ats_guidance.py
  - api/app/scanner/service.py
  - api/tests/test_pdf_readability.py
  - api/tests/test_html_renderer.py
  - api/tests/test_builders.py
  - api/tests/test_scanner_pdf_recovery.py
  - api/tests/test_scanner_ats_guidance.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/references/cv-guidelines.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-27T15:54:50.926023+00:00'
UPDATED_AT: '2026-09-27T15:54:50.926023+00:00'
---

# Improve CV project metadata and URL readability across templates

## Background

PDF project dates can extract after descriptions, link labels can hide destination URLs, and generated arrows can produce separate hyperlink annotations. Apply shared renderer fixes across templates and strengthen bounded PDF recovery diagnostics.

## Investigation

The reported PDF has intact link destinations, but visible project labels say
"GitHub" and profile labels expose usernames alone. Chromium emits separate
annotations over generated arrow glyphs. PDFium and Poppler raw extraction put
project dates after descriptions; pdfplumber's spatial extraction differs.
Workday reportedly creates broken employment entries from projects. Local
extraction reproduces structural risks, not Workday's classification itself.

## Decision

Apply metadata-before-body layout in the shared renderer for both supported
entry policies and all seeded templates. Preserve explicit labels and stored
destinations; compact only default URL labels. Accept supplied existing short
URLs through existing fields, without provisioning redirects. Keep the
canonical HTML/PDF pipeline and protocol v9. Scanner diagnostics must separate
local parser results from vendor compatibility claims.

## Implementation

In progress: shared renderer, bounded PDF diagnostics, tailoring guidance,
and synthetic real-PDF regression coverage. User's unrelated draft-retirement
and relocation changes remain intact.

## Verification

Initial real-PDF matrix passes 12 combinations: Modern, Classic, Minimal;
stack and two-column entry policies; continuous and forced-page-break output.
Assertions cover date/link-before-description order, repeated dates, a wrapped
URL with query and fragment, exact clickable targets, no generated arrows, and
physical page bounds. Both pdfplumber and PDFium are exercised; known PDFium
hyphen markers are verified before normalizing in test comparisons.

## Follow-up

Re-import a regenerated real CV into Workday to verify project classification
and website field behavior. No Workday compatibility certification is implied
by local tests. Existing tracker fork warnings are unrelated.
