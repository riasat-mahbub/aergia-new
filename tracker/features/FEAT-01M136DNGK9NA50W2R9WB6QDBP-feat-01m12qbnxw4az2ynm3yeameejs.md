---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M136DNGK9NA50W2R9WB6QDBP
TYPE: feature
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M12QBNXW4AZ2YNM3YEAMEEJS
AFFECTS: null
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-28T03:25:39.731368+00:00'
UPDATED_AT: '2026-08-28T03:25:39.731368+00:00'
---

# FEAT-01M12QBNXW4AZ2YNM3YEAMEEJS

## Background

Implemented singleton User profile API and Library Profile card; Research Library kind and editor/picker support; pure keyword-v1 relevance engine; Application ORM/API/service with generation provenance, ownership, status dates, retry and linked-CV deletion protection; canonical PDF render_payload/page counting and bounded one-page fitting; Applications list/detail/form UI, routes, navigation, Builder relevance context and post-save recomputation; smoke_live coverage. Files: api/app/models/application.py, api/app/models/user.py, api/app/models/__init__.py, api/app/routes/applications.py, api/app/routes/profile.py, api/app/routes/cvs.py, api/app/schema/models.py, api/app/schemas/application.py, api/app/schemas/profile.py, api/app/schemas/library.py, api/app/services/application.py, api/app/services/cv.py, api/app/services/library.py, api/app/services/pdf.py, api/app/services/profile.py, api/app/services/relevance.py, api/alembic/env.py, api/alembic/versions/9f3c5a8b7d21_add_user_profile_data.py, api/alembic/versions/a72e6d4c1b90_add_applications.py, api/scripts/smoke_live.py, web/src/lib/api/applications.ts, web/src/lib/api/profile.ts, web/src/lib/api/library.ts, web/src/lib/store/applicationStore.ts, web/src/lib/store/profileStore.ts, web/src/lib/store/libraryStore.ts, web/src/components/applications, web/src/components/library, web/src/components/sections/research/ResearchEditor.tsx, web/src/pages/ApplicationsPage.tsx, web/src/pages/ApplicationDetailPage.tsx, web/src/pages/BuilderPage.tsx, web/src/pages/LibraryPage.tsx, web/src/main.tsx. Verification: fresh-database pytest 418 passed; frontend Vitest 299 passed; ruff check app tests scripts passed; codegen:check passed; npm build passed; ./dev.sh --smoke passed; browser production flow created Example Labs linked CV, matched detail/Builder Relevance, and score decreased after Builder edit without regeneration.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
