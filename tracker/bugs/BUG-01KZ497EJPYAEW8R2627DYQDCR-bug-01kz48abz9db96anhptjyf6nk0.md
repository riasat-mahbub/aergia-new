---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KZ497EJPYAEW8R2627DYQDCR
TYPE: bug
STATUS: DONE
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
CREATED_AT: '2026-08-03T17:02:32.534353+00:00'
UPDATED_AT: '2026-08-03T17:02:32.534353+00:00'
---

# BUG-01KZ48ABZ9DB96ANHPTJYF6NK0

## Background

Fix shipped: useFieldArray gained a move() helper; SortableAccordionList hosts a per-section DndContext that calls onMove; six editors thread move through. Outer ContentSectionList DndContext handler now filters to section IDs only (dnd-kit nested DndContext does not isolate entry drags as the plan assumed; guard is the correct fix). Verified: focused unit tests pass (24/24), production build clean, live browser end-to-end drag persists across Save+Reload for all six list-based sections; outer section reorder still works.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
