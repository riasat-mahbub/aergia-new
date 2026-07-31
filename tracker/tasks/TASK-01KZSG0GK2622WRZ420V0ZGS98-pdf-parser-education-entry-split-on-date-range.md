---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KZSG0GK2622WRZ420V0ZGS98
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
CREATED_AT: '2026-08-11T22:45:08.322839+00:00'
UPDATED_AT: '2026-08-11T22:45:08.322839+00:00'
---

# pdf-parser: education entry split on date range

## Background

Task 4 of plan. _extract_education_fields relied on blank lines to delimit entries. Real-world resumes often omit blank lines between the date range of entry N and the degree of entry N+1. Re-implement _extract_education_fields to split on DATE_RANGE_RE matches: each date range closes one entry, the most recent degree-keyword line is the degree, the line immediately before is the institution. New test in api/tests/test_parser_imports.py.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
