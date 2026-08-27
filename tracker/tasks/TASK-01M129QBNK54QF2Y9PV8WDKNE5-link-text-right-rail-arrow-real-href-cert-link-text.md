---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNE5
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T20:33:54.214721+00:00'
UPDATED_AT: '2026-08-09T20:33:54.214721+00:00'
---

# Link text: right rail, arrow, real href, cert link_text

## Background

Shipped with docs/plans/2026-08-09-field-layout-fixes.md Task 4. projects/research/certifications link fields now align=right and carry TextStyle(link=url) so the renderer emits real <a href>; .f-link joins the 0.75rem size group and gets a ::after arrow. apply_field_text_styles merges instead of replacing so user styling never drops the builder href. Certifications gain an optional link_text field (editor + types + zod + builder, default 'Certificate'). Builder/renderer/validator tests added.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KZM3PS162ZC2CHE6TGF29R84 during the schema-4 cutover. -->
