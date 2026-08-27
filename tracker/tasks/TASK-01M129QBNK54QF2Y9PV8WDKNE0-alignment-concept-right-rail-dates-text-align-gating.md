---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNE0
TYPE: task
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  part_of:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN9N
AFFECTS:
  files:
  - api/app/schema/models.py
  - api/app/services/renderer/builders/*.py
  - api/app/services/renderer/html.py
  - web/src/components/customization/CustomizePanel.tsx
  - api/tests/test_builders.py
  - api/tests/test_html_renderer.py
  - web/src/components/__tests__/CustomizePanel.test.tsx
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T19:43:45.711490+00:00'
UPDATED_AT: '2026-08-09T19:43:45.711490+00:00'
---

# Alignment concept: right-rail dates + text-align gating

## Background

Revision 2 of the field-row layouts work: FieldBlock.align=right marks right-rail fields (dates, language proficiency); renderer pushes the first right-aligned field with margin-left:auto and mirrors section text_align as row justify-content when no rail is present (fixes the centering regression); builders re-grouped so main data is row 1, secondary row 2, summary terminal, skills single-row; CustomizePanel shows the text align control only for profile/skills/certifications.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KZM0TZ1FW5SK3XB1AB8M6AGJ during the schema-4 cutover. -->
