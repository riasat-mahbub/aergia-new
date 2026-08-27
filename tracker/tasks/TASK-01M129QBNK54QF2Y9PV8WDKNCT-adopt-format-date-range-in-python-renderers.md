---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNCT
TYPE: task
STATUS: IN_PROGRESS
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-02T02:20:05.342539+00:00'
UPDATED_AT: '2026-08-02T02:20:05.342539+00:00'
---

# Adopt format_date_range in Python renderers

## Background

Replace hand-rolled date strings in api/app/services/renderer/section_renderers/{experience,education,projects,certifications}.py with format_date_range. Education GPA moves to its own line. Projects link uses link_text || url. Existing tests (test_section_renderers.py) must stay green.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KZ04AXAYBYC2037KGBW522AH during the schema-4 cutover. -->
