---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1PQG19ZFM7N9ZYBQ3XWNH4A
TYPE: task
STATUS: PLANNED
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT
AFFECTS:
  files:
  - web/src/pages/CvListPage.tsx
  - web/src/components/cv-list/
  - web/src/components/__tests__/CvList.test.tsx
  - web/src/main.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T17:29:37.343579+00:00'
UPDATED_AT: '2026-09-04T17:29:37.343579+00:00'
---

# CV list page ownership

## Background

Step 1 of the page-oriented frontend migration. Move the CV list page and its page-owned components and tests into a feature-local boundary; leave generic common components and shared stores/APIs unchanged. Parent plan: `FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT`.

## Investigation


## Decision


## Implementation

- Move `CvListPage` and the `cv-list` component/test files to `web/src/features/cv-list/`.
- Update only the CV-list route import and relative paths.
- Keep `components/common`, Zustand stores, API wrappers, and route URLs unchanged.


## Verification

- Run CV-list tests, frontend lint, production build, and codegen drift check.
- Confirm no other page or shared component moved in this step.


## Follow-up
