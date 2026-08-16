---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN9A
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS:
  files:
  - web/src/lib/sections/types.ts
  - web/src/components/sections/skills/SkillsRenderer.tsx
  - web/src/components/sections/SectionRegistry.tsx
  - web/src/components/sections/SectionPreviewPanel.tsx
  - web/src/components/customization/CustomizePanel.tsx
  - web/src/pages/BuilderPage.tsx
  - api/app/schemas/sections.py
  - api/app/services/renderer/section_renderers/skills.py
  - web/src/pages/__tests__/BuilderPage.handleUpdateStyle.test.ts
  - web/src/components/__tests__/CustomizePanel.test.tsx
  - api/tests/test_section_renderers.py
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-04T18:23:34.997432+00:00'
UPDATED_AT: '2026-08-04T18:23:34.997432+00:00'
---

# Skills section inline layout variant

## Background

Add a per-section block/inline layout selector for Skills and preserve it through preview, PDF, and CV persistence.

## Investigation

Existing per-instance styles already flow through the JSON section schema and renderer context. The backend renderer is authoritative for iframe preview and PDF; the React renderer remains a parity preview.

## Decision

Use optional `SectionStyle.layout` with `block` as the missing-field default and `inline` as the only alternate. Reuse `f-category` and `f-tag` hooks so field typography remains effective.

## Implementation

Added matching TypeScript/Pydantic fields, renderer branches, registry style threading, a Skills-only Customize selector, and style-object persistence checks.

## Verification

Focused backend suite: 32 passed. Frontend production build passed. Focused frontend suite passes all new tests and retains the documented pre-existing `Body Font` failure.

## Follow-up

<!-- Migrated from FEAT-01KZ708J2NVNK63N0R4QHX7ZGM during the schema-4 cutover. -->
