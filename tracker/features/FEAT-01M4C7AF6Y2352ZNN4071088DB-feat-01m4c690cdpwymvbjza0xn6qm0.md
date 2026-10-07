---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M4C7AF6Y2352ZNN4071088DB
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: High
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M4C690CDPWYMVBJZA0XN6QM0
  depends_on:
  - TASK-01M4C327TAVB7AX3GK7SY85QEY
AFFECTS:
  files:
  - api/app/db/seed.py
  - api/app/http_schemas/profile.py
  - api/app/scanner/ats_guidance.py
  - api/app/scanner/ats_results.py
  - api/app/scanner/service.py
  - api/app/services/renderer/builders/_utils.py
  - api/app/services/renderer/builders/profile.py
  - api/app/services/renderer/html_renderer/html_document.py
  - api/app/services/renderer/html_values.py
  - api/app/services/tailoring.py
  - api/tests/test_format_single_date.py
  - api/tests/test_html_renderer.py
  - api/tests/test_minimal_readability.py
  - api/tests/test_page_margin_geometry.py
  - api/tests/test_pdf_readability.py
  - api/tests/test_profile_urls_prompts.py
  - api/tests/test_scanner_ats_guidance.py
  - api/tests/test_scanner_backfill.py
  - api/tests/test_seed_templates.py
  - api/tests/test_tailoring_v10_context.py
  - api/tests/test_tailoring_v10_lifecycle.py
  - web/scripts/test-preview-pagination.mjs
  - web/scripts/test-profile-links-prompts.mjs
  - web/src/features/builder/components/preview/UserTemplateRenderer.tsx
  - web/src/features/builder/components/preview/pageGeometry.ts
  - web/src/features/builder/components/preview/pagePagination.ts
  - web/src/features/profile/components/UserProfileEditor.tsx
  - web/src/features/profile/types/index.ts
  - web/src/shared/cv-editor/section-editors/experience/ExperienceEditor.tsx
  - web/src/shared/cv-editor/section-editors/profile/ProfileEditor.tsx
  - web/src/shared/cv/date.ts
  - web/src/shared/cv/date.test.ts
  - web/src/shared/cv/sectionCatalog.ts
  - web/src/shared/cv/sectionData.ts
  - docs/plans/2026-10-07-cv-professional-fixes.md
  - docs/fixtures/cv-professional-fixes/README.md
  - docs/fixtures/cv-professional-fixes/integration-review.md
  - docs/fixtures/cv-professional-fixes/pdf-measurements.json
  - docs/fixtures/cv-professional-fixes/preview-measurements.json
  - docs/fixtures/cv-professional-fixes/mobile-measurements.json
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-10-07T22:21:38.910421+00:00'
UPDATED_AT: '2026-10-07T22:21:38.910421+00:00'
---

# Improve Classic and Minimal professional CV defaults

## Background

Implemented audit C01-C06 with Luna6 max agents: Classic readable defaults, repeating PDF/preview margins, clear date ranges/scanner guidance, opt-in visible URLs and tailoring preference freshness, factual prompts, and oversized-entry advice. Reviewed checkpoint 02f4fd6. Final backend 978 passed/1 skipped; frontend lint/typecheck, architecture, codegen, browser fixtures, tailoring tests and release smoke passed. Preserved authored styles/padding/labels and Modern multi-zone sizing; oversized preview remains approximate. Evidence in docs/fixtures/cv-professional-fixes/ and docs/plans/2026-10-07-cv-professional-fixes.md.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
