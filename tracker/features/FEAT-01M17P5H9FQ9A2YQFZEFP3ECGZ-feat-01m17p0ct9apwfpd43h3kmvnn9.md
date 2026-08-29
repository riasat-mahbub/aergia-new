---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M17P5H9FQ9A2YQFZEFP3ECGZ
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS:
- applications
- relevance
- cv-generation
- testing
RELATIONS:
  supersedes:
  - FEAT-01M17P0CT9APWFPD43H3KMVNN9
AFFECTS:
  files:
  - api/app/schemas/application.py
  - api/app/services/application.py
  - api/app/services/cv.py
  - api/app/services/pdf.py
  - api/app/services/relevance.py
  - api/app/services/relevance_taxonomy.py
  - api/scripts/cleanup_application_artifacts.py
  - api/scripts/smoke_live.py
  - api/tests/conftest.py
  - api/tests/test_applications_fit.py
  - api/tests/test_applications_generation.py
  - api/tests/test_cleanup_application_artifacts.py
  - api/tests/test_requirement_relevance.py
  - web/src/components/applications/RelevanceDrawer.tsx
  - web/src/components/applications/__tests__/RelevanceDrawer.test.tsx
  - web/src/lib/api/applications.ts
  - docs/plans/2026-08-29-evidence-driven-application-cv-selection.md
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-29T21:17:48.207526+00:00'
UPDATED_AT: '2026-08-29T21:17:48.207526+00:00'
---

# Evidence-driven application CV selection and test-data cleanup

## Background

Completed section-aware requirement-v2 selection and relevance-aware fitting. Cleaned api/data/aergia.db (2 applications, 2 linked CVs removed, 37 unrelated CVs preserved) and api/data/aergia.test.db (100 applications, 75 linked CVs removed, 317 unrelated CVs preserved); skipped smoke DB with no application schema. Frontend: 344 tests passed, build and codegen check passed. Backend Ruff and direct unit scenarios passed; pytest integration remains blocked by aiosqlite hanging on connection startup under Python 3.14 in this environment.

## Investigation

- The previous selector used greedy requirement coverage and a fixed reverse
  section priority for page fitting.
- CV metadata is user-editable, so cleanup uses only `applications.cv_id` as
  provenance and preserves metadata-only CVs.


## Decision

- Profile is mandatory; populated education is the baseline CV content.
- Other sections compete using job-specific evidence and complementary proof;
  no semantic fixed hierarchy is applied.
- New results use requirement-v2 and old persisted result shapes remain
  readable.
- Local application cleanup is explicit, backed up, transactional, and
  limited to disposable records.


## Implementation

- Added section-aware requirement cues and certification aliases.
- Added marginal Library selection, complementary evidence, coverage scoring,
  selection metadata, and relevance-aware page fitting.
- Added PDF runtime fallback, safe database cleanup, fresh pytest databases,
  smoke scenario coverage, and UI/backend regression tests.


## Verification

- Cleaned both local application databases with the expected preservation
  counts; skipped the schema-less smoke database.
- Frontend tests: 344 passed. Frontend build and codegen check passed.
- Ruff and direct backend unit scenarios passed.
- Full backend pytest is blocked by aiosqlite hanging during connection startup
  under the local Python 3.14 runtime.


## Follow-up
