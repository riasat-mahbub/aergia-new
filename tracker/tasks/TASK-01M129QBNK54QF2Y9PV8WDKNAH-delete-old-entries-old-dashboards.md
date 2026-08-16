---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNAH
TYPE: task
STATUS: PLANNED
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- plan
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:03:33.700208+00:00'
UPDATED_AT: '2026-08-01T16:03:33.700208+00:00'
---

# Delete old entries + old dashboards

## Background

`git rm tracker/bugs/00*.md tracker/features/00*.md tracker/issues/ tracker/bugs/index.md tracker/features/index.md`. Verify: find tracker -name "*.md" | wc -l = 44 new entries + README.md + _template.md; no 0-prefixed files or issues/ dir remain.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KYZ120P4893W9G2DT2W6DZMT during the schema-4 cutover. -->
