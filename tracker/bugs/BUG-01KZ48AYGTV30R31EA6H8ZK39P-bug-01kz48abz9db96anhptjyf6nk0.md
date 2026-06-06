---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KZ48AYGTV30R31EA6H8ZK39P
TYPE: bug
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01KZ48ABZ9DB96ANHPTJYF6NK0
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-03T16:46:58.586210+00:00'
UPDATED_AT: '2026-08-03T16:46:58.586210+00:00'
---

# BUG-01KZ48ABZ9DB96ANHPTJYF6NK0

## Background

Root cause confirmed: SortableAccordionList registers sortable entries under the outer section DndContext, whose handler ignores entry IDs. Implementing an entry-scoped DndContext and shared array move helper.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
