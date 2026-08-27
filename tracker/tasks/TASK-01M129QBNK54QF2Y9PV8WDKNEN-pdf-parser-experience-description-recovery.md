---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNEN
TYPE: task
STATUS: PROPOSED
PRIORITY: High
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- parser
- fix
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-11T22:45:08.344779+00:00'
UPDATED_AT: '2026-08-11T22:45:08.344779+00:00'
---

# pdf-parser: experience description recovery

## Background

Task 3 of plan. _extract_experience_fields only collected description lines that matched the bullet regex. Modern resumes write running paragraphs. Open the description gate: every non-meta, non-date line is a description sentence for the current entry until the next entry's position+company pair or the next date range. Bullet regex becomes a strip, not a gate. New tests in api/tests/test_parser_imports.py.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KZSG0GKRKY76E3DM125F5M6D during the schema-4 cutover. -->
