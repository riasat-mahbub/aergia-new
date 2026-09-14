---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M2GMQB8T01HHAXQRXRWRS3EB
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - FEAT-01M14M2M1ATV0C4CSZ8K3QB2EY
  - ADR-01M29BGP0TN064SDB93RKRW7ST
AFFECTS:
  files:
  - api/app/models/application.py
  - api/app/models/cv.py
  - api/app/models/tailoring_session.py
  - api/app/services/application.py
  - api/app/services/cv.py
  - api/app/services/tailoring.py
  - api/alembic/versions/n9o0p1q2_add_cv_application_ownership.py
  - api/tests/test_applications_generation.py
  - api/tests/test_cv_application_ownership_migration.py
  - api/tests/test_cvs.py
  - api/tests/test_tailoring.py
  - web/src/features/cvs/pages/CvListPage.tsx
  - web/src/features/dashboard/pages/DashboardPage.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-14T19:01:26.426086+00:00'
UPDATED_AT: '2026-09-14T19:01:26.426086+00:00'
---

# Application-associated CVs reappear in the reusable CV list

## Background

Application-generated CVs are hidden only while applications.cv_id points at them, so replaced CVs and review drafts can appear as reusable CVs. Persist a nullable cvs.application_id association while retaining applications.cv_id as the current CV pointer; backfill from durable relational references only.

## Investigation

The CV list summary used ``applications.cv_id`` as both the current-CV
pointer and the only reverse provenance link. When that pointer changed, an
older application CV lost its application summary; submitted drafts also had
no relational application link. CV metadata cannot safely recover provenance
because users can edit it.

## Decision

Add a nullable many-to-one ``cvs.application_id`` association. Keep
``applications.cv_id`` as the single current/primary CV pointer so a draft
remains a candidate until its owner accepts it.

## Implementation

Added the indexed FK and backfilled it from current application pointers and
durable tailoring-session source/draft references, checking ownership and
leaving ambiguous references untouched. Standard generation and tailoring
submission now associate CVs at creation; acceptance still switches only the
current pointer. CV summaries use the new relation, application deletion
detaches all associated CVs, and copies remain unassociated.

## Verification

The SQLite migration contract passes with FK enforcement enabled and covers
backfill, ambiguous/foreign-owner rows, and downgrade. Ruff, model mapper
configuration, Python syntax parsing, and the Alembic head check pass. The
smoke gate passed backend Ruff, frontend lint, and frontend build, then timed
out during Alembic initialization under Python 3.14; async SQLite connection
startup also times out in this environment.

## Follow-up

Previously displaced CVs with no surviving application or tailoring-session
reference remain unassociated; their provenance cannot be inferred safely
from editable metadata.
