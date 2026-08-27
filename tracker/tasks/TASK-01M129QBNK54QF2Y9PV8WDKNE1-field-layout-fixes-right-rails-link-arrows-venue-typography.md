---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNE1
TYPE: task
STATUS: PLANNED
PRIORITY: Medium
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS:
  files:
  - api/app/services/renderer/builders/experience.py
  - api/app/services/renderer/builders/education.py
  - api/app/services/renderer/builders/projects.py
  - api/app/services/renderer/builders/research.py
  - api/app/services/renderer/builders/certifications.py
  - api/app/services/renderer/builders/__init__.py
  - api/app/services/renderer/html.py
  - api/tests/test_builders.py
  - api/tests/test_html_renderer.py
  - web/src/components/sections/research/ResearchEditor.tsx
  - web/src/components/sections/certifications/CertificationsEditor.tsx
  - web/src/lib/sections/types.ts
  - web/src/lib/validators/sections.ts
  - web/src/lib/sections/fieldStyles.ts
  - web/src/components/builder/ContentSectionList.tsx
  - docs/plans/2026-08-09-field-layout-fixes.md
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T20:22:16.368288+00:00'
UPDATED_AT: '2026-08-09T20:22:16.368288+00:00'
---

# Field-layout fixes: right rails, link arrows, venue, typography

## Background

Plan: docs/plans/2026-08-09-field-layout-fixes.md. Fixes 9 reported issues: Publication Venue typo + missing venue in preview, right-rail location/GPA/link/cert-date, link arrows + cert link_text, typography consistency off experience/education, exclusive content accordions. No schema/manifest/resolver changes; builder-emitted AST data + renderer CSS only.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KZM31FHGN5XVQEB423MVC36C during the schema-4 cutover. -->
