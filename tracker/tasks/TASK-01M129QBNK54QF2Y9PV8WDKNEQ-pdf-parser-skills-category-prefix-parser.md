---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNEQ
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
CREATED_AT: '2026-08-11T22:45:08.368223+00:00'
UPDATED_AT: '2026-08-11T22:45:08.368223+00:00'
---

# pdf-parser: skills category prefix parser

## Background

Task 5 of plan. _extract_skills_fields collapsed 'Programming Languages: TypeScript, JavaScript' into ['Programming Languages: TypeScript', 'JavaScript', ...]. Split skills text on lines first; peel lines starting with '^([A-Z][A-Za-z0-9 &/+-]+):\s*' into category + items. _extract_skills_fields now returns list[{'category', 'items'}]; the mapper already consumed that shape. New test in api/tests/test_parser_imports.py.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KZSG0GMGPDMPH6SK8JAFK1R4 during the schema-4 cutover. -->
