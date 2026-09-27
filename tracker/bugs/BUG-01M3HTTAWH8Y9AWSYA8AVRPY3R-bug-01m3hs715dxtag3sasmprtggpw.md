---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3HTTAWH8Y9AWSYA8AVRPY3R
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01M3HS715DXTAG3SASMPRTGGPW
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
  - api/app/scanner/ats_results.py
  - api/app/scanner/service.py
  - api/tests/test_pdf_readability.py
  - api/tests/test_html_renderer.py
  - api/tests/test_builders.py
  - api/tests/test_render_links.py
  - api/tests/test_scanner_pdf_recovery.py
  - api/tests/test_scanner_readability.py
  - api/tests/test_scanner_ats_guidance.py
  - api/tests/test_scanner_backfill.py
  - api/tests/test_tailoring.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/references/cv-guidelines.md
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-27T16:22:52.049259+00:00'
UPDATED_AT: '2026-09-27T16:22:52.049259+00:00'
---

# Improve CV project metadata and URL readability across templates

## Background

Implemented shared template metadata and URL readability, bounded dual-parser diagnostics, tailoring guidance, and real-PDF regression coverage. Full backend: 817 passed, 1 skipped; release smoke passed.

## Investigation

The supplied PDF retained clickable destinations but printed generic labels and
separate arrow annotations. PDFium placed project dates after descriptions;
pdfplumber associated them spatially. The actual scanner reproduced this
disagreement on the supplied PDF. Local extraction cannot reproduce Workday's
proprietary project classification.

## Decision

Use the shared HTML renderer for all templates. Preserve explicit labels,
destination URLs, editor settings, document schema, and tailoring protocol v9.
Existing URL fields accept user-supplied short URLs; no redirects are provisioned.

## Implementation

Projects, research, and certifications place title/date and other metadata before
full-width link rows and descriptions for either entry policy. Generated arrows
are removed. Default URL labels omit scheme and leading www but retain paths,
queries, and fragments; long addresses wrap without reducing font size.

Resource-bounded PDF diagnostics now compare date association, visible addresses,
clickable links, and agreement between pdfplumber and PDFium. Verified PDFium
hyphen sentinels are restored without masking unmapped glyphs. Analysis and render
freshness versions were bumped. Tailoring guidance distinguishes factual project
headings from work experience and favors readable addresses. Unrelated user
draft-retirement and relocation edits remain intact.

## Verification

- Full backend: 817 passed, 1 skipped. Ruff and diff whitespace checks passed.
- Twelve real Chromium PDF cases cover Modern, Classic, Minimal; stack and
  two-column entries; continuous and forced page breaks. They verify both parser
  outputs, repeated dates, wrapped URLs with query/fragment, exact destinations,
  absence of generated arrows, and physical page bounds.
- Actual scanner on synthetic PDFs: all templates recover 4/4 date associations,
  4/4 clickable links, and 4/4 visible addresses. Classic and Minimal agree across
  parsers; Modern reports sidebar reading-order disagreement.
- Frontend lint, typecheck, architecture tests/check, and codegen check passed.
  Existing hook warnings remain. Tailoring Node test passed.
- Final ./dev.sh --smoke passed, including build, isolated database migration,
  SSR, nonce CSP, gateway, and root-scoped cookies.
- Synthetic PDF previews were generated and visually inspected. Stale renderer
  assertions and the bundle test's existing reference-file list were corrected.

## Follow-up

Re-export the real CV and import it into Workday to confirm project classification
and website fields. Modern's sidebar reading order remains parser-dependent;
local diagnostics do not certify compatibility with any ATS.
