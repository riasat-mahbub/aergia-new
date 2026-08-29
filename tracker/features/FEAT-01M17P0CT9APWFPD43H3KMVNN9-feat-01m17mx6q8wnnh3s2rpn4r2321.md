---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M17P0CT9APWFPD43H3KMVNN9
TYPE: feature
STATUS: IN_PROGRESS
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
  - FEAT-01M17MX6Q8WNNH3S2RPN4R2321
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
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-29T21:14:59.785716+00:00'
UPDATED_AT: '2026-08-29T21:14:59.785716+00:00'
---

# Evidence-driven application CV selection and test-data cleanup

## Background

Implemented requirement-v2 section-aware extraction and marginal Library selection; profile/education baseline, dynamic certification/skill-project/research evidence, weighted coverage diagnostics, relevance-aware fitting, PDF-unavailable CV creation, cleanup utility, and fresh pytest DB isolation. Direct SQLite and frontend checks pass; backend integration tests remain blocked by the local aiosqlite connection hang.

## Investigation

- The previous selector used greedy requirement coverage plus a fixed reverse
  section priority during page fitting.
- CV metadata is user-editable, so only `applications.cv_id` identifies a
  generated CV for cleanup. Metadata-only CVs remain untouched.


## Decision

- Profile is mandatory; populated education is a baseline.
- All other sections compete by job-specific marginal evidence and
  complementary proof. No semantic fixed hierarchy is used.
- Requirement-v2 is used for new results; persisted v1 shapes remain readable.
- Cleanup is explicit, backed up, transactional, and limited to local test
  databases.


## Implementation

- Added section-aware requirement cues, certification taxonomy aliases,
  complementary Library selection, coverage scoring, selection metadata, and
  relevance-aware page fitting.
- Added PDF runtime fallback that creates a CV with unknown page-fit status.
- Added cleanup utility, fresh pytest database setup, smoke scenario cues, and
  backend/frontend regression tests.


## Verification

- Requirement selection scenarios pass through direct deterministic checks.
- Cleanup scenarios pass against temporary SQLite databases.
- Ruff, frontend build, and focused relevance UI tests pass.
- Full backend pytest remains to be rerun in an environment where aiosqlite
  connections complete.


## Follow-up
