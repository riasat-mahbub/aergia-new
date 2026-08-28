---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M153EFMSAFDAYC8A1ZS3FSJ0
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
  - FEAT-01M152GH11G9XSRRPXRF7K8V2Z
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
CREATED_AT: '2026-08-28T21:12:09.625695+00:00'
UPDATED_AT: '2026-08-28T21:12:09.625695+00:00'
---

# FEAT-01M152GH11G9XSRRPXRF7K8V2Z

## Background

Implemented language-aware application CV generation, deterministic skill-item-first fit trimming, persisted status history and next follow-up dates, client-side application search operators, relevance evidence drawer, and stored CV quality checks for contact details, empty sections, safe links, and page count. Focused backend tests: 19 passed; frontend full suite: 341 passed; backend full suite: 449 passed with 7 known pre-existing/repeatable failures outside this feature; full frontend lint remains blocked by existing no-explicit-any errors.

## Investigation

The existing application record stored only its current status and relevance
summary. Library relevance already recognized language entries at the schema
boundary, but the scorer did not include them in its eligible fields. The
existing fit loop removed complete rows, so a low-value skill chip could cause
an otherwise useful skill group to disappear.

## Decision

Keep application filtering local because the application list is already
loaded for the single-user dashboard. Use explicit search operators for
structured filters while retaining free-text matching. Store immutable status
transitions and deterministic CV quality results alongside the application;
quality link checks validate safe syntax only and never perform network calls.

## Implementation

Added language-aware row scoring/materialization, skill-item scoring and
item-first fit reduction, a status-history table with migration backfill, and
date-only follow-up persistence. Added application search operators, a
right-side relevance drawer with evidence, and quality checks for contact
details, empty sections, safe links, and rendered page count.

## Verification

Focused backend tests pass (19); frontend tests pass (341); code generation,
frontend production build, and Ruff pass. The full backend run passes 449
tests; its seven failures are existing/repeatable asset fixture, upload-size,
test-database isolation, and removed-route expectations. Full frontend lint
still reports the repository's existing no-explicit-any errors.

## Follow-up
