---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M17MX6Q8WNNH3S2RPN4R2321
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
  depends_on:
  - FEAT-01M159T437M7QTNCEPRD4M0WHJ
AFFECTS:
  files:
  - api/app/services/relevance.py
  - api/app/services/application.py
  - api/app/services/cv.py
  - api/app/schemas/application.py
  - api/scripts/cleanup_application_artifacts.py
  - api/tests/conftest.py
  - api/tests/test_requirement_relevance.py
  - api/tests/test_applications_generation.py
  - web/src/lib/api/applications.ts
  - web/src/components/applications/RelevanceDrawer.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-29T20:55:46.664846+00:00'
UPDATED_AT: '2026-08-29T20:55:46.664846+00:00'
---

# Evidence-driven application CV selection and test-data cleanup

## Background

Replace fixed section ordering with evidence-driven Library selection while preserving profile and education baselines; improve scoring and fitting diagnostics; clean disposable application data across local databases; isolate pytest data.

## Investigation

- The current selector greedily covers requirements but has no section-aware
  evidence policy. Profile is materialized separately, education is a weak
  fallback, and the fit loop uses a fixed reverse section priority.
- The local databases contain disposable application data. Generated CVs are
  identified only by the `applications.cv_id` relation because CV metadata is
  user-editable; all unlinked CVs must remain untouched.


## Decision

- Profile is mandatory and never trimmed.
- Populated education is a baseline CV section and is trimmed only after lower
  value content; at least one entry is retained when possible.
- All other sections are ranked by marginal weighted job evidence. There is no
  fixed hierarchy between experience, skills, certifications, languages,
  projects, and research. Requirement-specific evidence and complementary
  proof decide the result; stable row order resolves exact ties.
- New generation uses requirement-v2 while legacy results remain readable.
- Application cleanup is transactional and explicit per database, with a
  recoverable backup and dry-run mode. Only relationally linked CVs are
  removed; no production data migration is added.


## Implementation

- Replace fixed section fallback and fit removal with evidence-aware row and
  skill-item scoring.
- Add section affinities and complementary evidence scoring for certifications,
  skills/projects, research, education, and experience.
- Add coverage diagnostics and selection metadata without changing generation
  endpoints or adding user controls.
- Add a safe local database cleanup utility and isolate pytest databases.


## Verification

- Benchmark cases cover CCNA certification requirements, React skill-plus-
  project evidence, research/publication requirements, baseline education, and
  irrelevant optional sections.
- Cleanup verification proves applications and generated CVs are removed while
  unrelated CVs remain byte-for-byte represented in the database.


## Follow-up
