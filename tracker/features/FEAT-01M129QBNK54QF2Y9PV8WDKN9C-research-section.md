---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN9C
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- sections
- research
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-04T18:43:44.149570+00:00'
UPDATED_AT: '2026-08-04T18:43:44.149570+00:00'
---

# research-section

Add a new repeatable `research` section type for academic publications. Each
entry stores a required title and description, an optional paper URL with
separate display text, and an optional publication date; it must be selectable
anywhere section types are offered and persist through the existing CV JSON
section pipeline. Research renders as a left-bordered publication citation card
— deliberately distinct from Projects.

## Affected files

- `web/src/lib/sections/types.ts` — ResearchEntry, SECTION_LABELS, SECTION_TYPES, createDefaultSectionData
- `web/src/lib/validators/sections.ts` — researchEntrySchema
- `web/src/lib/validators/validateSection.ts` — ARRAY_SECTION_SCHEMAS.research
- `web/src/lib/sections/sampleData.ts` — sample research entry
- `web/src/lib/sections/fieldStyles.ts` — field-style defs
- `web/src/components/sections/SectionRegistry.tsx` — register research
- `web/src/components/sections/AddSectionModal.tsx` — BookOpen icon
- `web/src/components/sections/research/ResearchEditor.tsx` — new
- `web/src/components/sections/research/ResearchRenderer.tsx` — new
- `web/src/lib/validators/__tests__/sections.test.ts` — researchEntrySchema tests
- `web/src/components/__tests__/AddSectionModal.test.tsx` — modal coverage
- `web/src/components/__tests__/SectionEditors.test.tsx` — editor coverage
- `api/app/schemas/sections.py` — ResearchEntry + SECTION_DATA_MODELS
- `api/app/services/renderer/section_renderers/research.py` — new
- `api/app/services/renderer/section_renderers/__init__.py` — register render_research
- `api/app/services/renderer/section_renderers/profile.py` — SECTION_LABELS
- `api/app/db/seed.py` — SEED_TEMPLATES placement + section_schema
- `api/tests/test_section_renderers.py` — research renderer tests

## Implementation

Complete: frontend types, validator, editor, renderer, registry, modal icon;
backend Pydantic schema, renderer, registry, seed placements, sample data,
field-style defs. Round-trip + multi-template preview + 12 renderer
contract tests pass. Frontend build + targeted Vitest (37 tests) green.
API-level smoke confirmed citation-card output across modern/classic/minimal
templates.

## Verification

- `npm run test -- --run src/lib/validators/__tests__/sections.test.ts
  src/components/__tests__/AddSectionModal.test.tsx
  src/components/__tests__/SectionEditors.test.tsx` — 37 passed
- `npm run build` — clean (no TS errors)
- `.venv/bin/pytest tests/test_section_renderers.py tests/test_sections.py
  tests/test_preview.py tests/test_cascading_styles.py` — 60 passed
- `api/tests/test_section_renderers.py` research suite — 12 passed
- Live API smoke: created CV with one research entry, rendered preview
  through all 3 system templates; all assertions (citation card, title,
  link label, ↗ glyph, publication date, description, URL normalization,
  iframe-safe href="#") confirmed.


## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from FEAT-01KZ71DEWNTWMBGSZR451RC81Z during the schema-4 cutover. -->
