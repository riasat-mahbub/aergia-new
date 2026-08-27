---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M12J8D95S46SWJ1A6XEA1YPK
TYPE: task
STATUS: PROPOSED
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- cleanup
RELATIONS: null
AFFECTS:
  files:
  - .gitignore
  - tracker/.gitignore
  - tracker/.tantivy/
  - .omp/agent/sessions/
  - docs/doc-audit-and-readme-plan.md
  - web/probe.cjs
  - api/alembic/versions/.gitkeep
  - api/app/services/renderer/builders/_utils.py
  - api/app/services/parser/_fonts.py
  - api/app/services/parser/imports.py
  - api/app/services/renderer/tokens.py
  - api/app/routes/cvs.py
  - api/app/services/parser/providers/gemini.py
  - web/src/components/layout/SectionZoneView.tsx
  - web/src/components/customization/ZoneStyleEditor.tsx
  - web/src/components/customization/ZoneCreationModal.tsx
  - web/src/lib/sections/zones.ts
  - web/src/lib/sections/fieldStyles.ts
  - web/src/components/customization/TemplateSelectorModal.tsx
  - web/src/components/preview/TemplateSwitcher.tsx
  - web/src/pages/BuilderPage.tsx
  - web/src/components/preview/UserTemplateRenderer.tsx
  - web/src/lib/api/cvs.ts
  - web/src/lib/store/libraryStore.ts
  - web/src/lib/api/render.ts
  - web/src/lib/store/supportStore.ts
  - web/src/styles/tokens.ts
  - web/index.html
  - web/package.json
  - web/package-lock.json
  - AGENTS.md
  - api/tests/test_extract_fonts.py
  - api/tests/test_auth.py
  - api/tests/test_templates.py
  - api/tests/test_render_links.py
  - web/src/lib/sections/DateField.tsx
  - web/src/pages/__tests__/BuilderPage.handleUpdateStyle.test.ts
  - web/src/components/__tests__/ContentSectionList.test.tsx
  - api/app/services/parser/mapper.py
  - api/app/services/renderer/html.py
  - api/tests/test_smoke_live.py
  - web/eslint.config.js
  - web/src/components/sections/rich-text/RichTextEditor.tsx
  - web/src/components/library/__tests__/LibraryPicker.test.tsx
  - web/src/lib/store/__tests__/supportStore.test.ts
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-27T21:33:15.942033+00:00'
UPDATED_AT: '2026-08-27T21:33:15.942033+00:00'
---

# Remove obsolete repository artifacts

## Background

Audit and remove unreachable code, generated/session artifacts, false or duplicate tests, stale one-shot documentation, and redundant metadata without changing supported behavior.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
