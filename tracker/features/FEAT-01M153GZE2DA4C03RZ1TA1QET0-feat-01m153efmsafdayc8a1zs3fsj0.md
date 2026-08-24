---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M153GZE2DA4C03RZ1TA1QET0
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: riasat
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M153EFMSAFDAYC8A1ZS3FSJ0
AFFECTS:
  files:
  - api/alembic/versions/c4e1f2a3b4c5_add_application_history_quality.py
  - api/app/models/application.py
  - api/app/schemas/application.py
  - api/app/services/application.py
  - api/app/services/quality.py
  - api/app/services/relevance.py
  - api/tests/test_applications.py
  - api/tests/test_applications_generation.py
  - api/tests/test_quality.py
  - api/tests/test_relevance.py
  - web/src/components/applications/ApplicationCard.tsx
  - web/src/components/applications/ApplicationFormModal.tsx
  - web/src/components/applications/RelevanceDrawer.tsx
  - web/src/components/applications/applicationPresentation.ts
  - web/src/lib/api/applications.ts
  - web/src/pages/ApplicationDetailPage.tsx
  - web/src/pages/ApplicationsPage.tsx
  - web/src/components/applications/__tests__/applicationPresentation.test.ts
  - web/src/pages/__tests__/ApplicationDetailPage.test.tsx
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-28T21:13:31.330989+00:00'
UPDATED_AT: '2026-08-28T21:13:31.330989+00:00'
---

# FEAT-01M153EFMSAFDAYC8A1ZS3FSJ0

## Background

Refined the relevance drawer backdrop accessibility label and displayed source identifiers for each evidence item; final build and test verification remains green.

## Investigation


## Decision


## Implementation

Refined the drawer to expose evidence source identifiers and use a distinct
accessible backdrop dismissal label.

## Verification

Final frontend build, codegen drift check, focused backend tests, frontend
suite, Ruff, and diff checks pass.

## Follow-up
