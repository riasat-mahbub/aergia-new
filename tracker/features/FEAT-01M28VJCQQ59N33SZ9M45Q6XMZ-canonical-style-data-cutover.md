---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M28VJCQQ59N33SZ9M45Q6XMZ
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: High
TAGS:
- document-schema
- migration
- customization
RELATIONS:
  related:
  - FEAT-01M20YH3CH8BEVHM0KJTZY7QAX
  - ADR-01M129QBNK54QF2Y9PV8WDKN6W
AFFECTS:
  files:
  - .gitignore
  - api/README.md
  - api/alembic/versions/j5k6l7m8n9_drop_template_default_customizations.py
  - api/app/db/seed.py
  - api/app/document_schema/capabilities.py
  - api/app/document_schema/models.py
  - api/app/http_schemas/cv.py
  - api/app/models/template.py
  - api/app/services/cv.py
  - api/app/services/renderer/builders/__init__.py
  - api/app/services/renderer/resolution/context.py
  - api/app/services/renderer/resolution/sections.py
  - api/tests/test_cvs.py
  - api/tests/test_html_renderer.py
  - api/tests/test_schema.py
  - api/tests/test_seed_templates.py
  - api/tests/test_templates.py
  - web/src/features/builder/components/BuilderWorkspace.tsx
  - web/src/features/builder/components/customization/Inspector.tsx
  - web/src/features/builder/components/customization/controls/ResetFooter.tsx
  - web/src/features/builder/components/customization/groups/BodyTextGroup.tsx
  - web/src/features/builder/components/customization/groups/SpacingGroup.tsx
  - web/src/features/builder/components/customization/groups/stylePatches.ts
  - web/src/features/builder/components/preview/UserTemplateRenderer.tsx
  - web/src/features/builder/domain/documentCommands.ts
  - web/src/features/builder/hooks/useBuilderDocumentLoader.ts
  - web/src/features/builder/hooks/useTemplateManifest.ts
  - web/src/features/builder/hooks/useUnsavedChanges.ts
  - web/src/features/builder/types/render.ts
  - web/src/features/cvs/types/index.ts
  - web/src/generated/schema.ts
  - web/src/shared/cv/placement.ts
  - web/src/shared/cv/schema.ts
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: riasat1998
UPDATED_BY: riasat1998
CREATED_AT: '2026-09-11T18:27:08.663553+00:00'
UPDATED_AT: '2026-09-11T18:27:08.663553+00:00'
---

# Canonical style data cutover

## Background

Migrate persisted CV and template style/layout JSON to the canonical axis model, enforce strict schemas, remove read-time style and placement compatibility adapters, and drop template default_customizations storage.

## Investigation

The schema had already moved the editor to axis-shaped styles, but persisted
CVs could still contain CSS spacing values, old flat style keys, and
type-keyed placement. Runtime/frontend adapters converted those values on
read. Templates also retained an unused ``default_customizations`` column.

## Decision

Perform one explicit raw-JSON migration before strict Pydantic validation.
Canonical CV placement is keyed by section instance ID; template manifests
remain type-keyed. After migration, reject legacy keys with closed models and
remove the read-time adapters and obsolete template column. The migrator is
idempotent, transactional, dry-run by default, and creates a backup when it
writes.

## Implementation

The one-time raw-JSON conversion was run against the application database,
then removed along with its dedicated tests. Strict extra handling and
spacing-token types now apply across the document model; frontend state and
style controls use generated canonical types directly. New CVs write
instance-ID placement, and ``default_customizations`` is removed by Alembic
after migration.

## Verification

* ``ruff check .``
* ``npm run codegen:check``
* ``npm run typecheck``
* ``npm run lint`` (9 pre-existing hook-dependency warnings, no errors)
* ``npm run architecture:test`` and ``npm run architecture:check``
* The application database was migrated idempotently (63 CV rows; second dry
  run reported zero changes) with a timestamped backup.
* Direct schema validation passed; full API pytest/Alembic execution was
  blocked in this environment by an ``aiosqlite`` connection hang.

## Follow-up
