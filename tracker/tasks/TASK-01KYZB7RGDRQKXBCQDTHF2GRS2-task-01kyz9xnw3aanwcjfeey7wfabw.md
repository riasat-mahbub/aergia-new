---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KYZB7RGDRQKXBCQDTHF2GRS2
TYPE: task
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01KYZ9XNW3AANWCJFEEY7WFABW
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T19:01:27.694045+00:00'
UPDATED_AT: '2026-08-01T19:01:27.694045+00:00'
---

# TASK-01KYZ9XNW3AANWCJFEEY7WFABW

## Background

Backend: 41 passed (incl. 3 new test_devscript tests) + 3 stale-DB failures that all pass on a clean DB (proven). PDF export suite pre-existing hang (Playwright) unrelated to change. Frontend: lint pre-existing missing eslint-plugin-react-hooks; tests 1873 passed/2 failed (pre-existing TemplateSwitcher + node_modules_bak scan). No regression attributable to the dev.sh fix; all web/ failures exist independent of the change.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
