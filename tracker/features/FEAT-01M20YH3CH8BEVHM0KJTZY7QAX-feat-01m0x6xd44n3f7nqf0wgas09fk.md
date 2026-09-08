---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M20YH3CH8BEVHM0KJTZY7QAX
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M0XC59QWJH7GFVZXDJBBBBB8
AFFECTS:
  files:
  - api/app/document_schema/models.py
  - api/app/http_schemas/cv.py
  - api/app/services/renderer/builders/__init__.py
  - api/app/services/renderer/html.py
  - api/app/services/renderer/resolve.py
  - api/app/document_schema/__init__.py
  - api/tests/test_html_renderer.py
  - api/tests/test_schema.py
  - web/src/features/builder/BuilderPage.tsx
  - web/src/features/builder/components/BuilderWorkspace.tsx
  - web/src/features/builder/components/customization/Inspector.tsx
  - web/src/features/builder/components/customization/SectionInspector.tsx
  - web/src/features/builder/components/customization/controls/ColorChip.tsx
  - web/src/features/builder/components/customization/controls/ResetFooter.tsx
  - web/src/features/builder/components/preview/UserTemplateRenderer.tsx
  - web/src/features/builder/domain/customization/cascade.ts
  - web/src/features/builder/domain/customization/fieldsForInstance.ts
  - web/src/features/builder/domain/customization/styleDefaults.ts
  - web/src/features/builder/domain/sectionStyle.ts
  - web/src/shared/cv/schema.ts
  - web/src/styles/tokens.ts
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-08T16:44:56.593754+00:00'
UPDATED_AT: '2026-09-08T16:44:56.593754+00:00'
---

# FEAT-01M0X6XD44N3F7NQF0WGAS09FK

## Background

Implemented section-local Customize controls: all section cards start closed, editable document style controls are removed, typography and independent spacing controls are available per section, renderer/schema cascade local typography and entry/field gaps, reset preserves layout placement, and preview renders without a saved layout.

## Investigation


## Decision


## Implementation

- Removed the editable document-style strip and made section cards an
  exclusive accordion that starts with every card closed.
- Added section typography roles for heading and body font family, size,
  line-height, color, and renderer-safe inheritance.
- Added independent `spacing_before`, `spacing_after`, `entry_gap`, and
  `field_gap` controls and applied each value to its own rendered boundary.
- Preserved template/global values as read-only inherited fallbacks, added
  section reset behavior, and kept zone placement during reset.
- Fixed preview rendering when a CV has no saved custom layout and synced
  color drafts when the selected section changes.

## Verification

- `npm run typecheck`
- `npm run lint` (existing hook-dependency warnings only)
- `npm run codegen:check`
- `npm run architecture:test`
- `npm run architecture:check`
- Python compile check passed.
- Focused schema, resolver, and renderer test functions passed (96 total).

## Follow-up
