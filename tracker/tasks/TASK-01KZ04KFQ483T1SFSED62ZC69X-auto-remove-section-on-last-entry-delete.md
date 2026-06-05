---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KZ04KFQ483T1SFSED62ZC69X
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
CREATED_AT: '2026-08-02T02:24:46.308195+00:00'
UPDATED_AT: '2026-08-02T02:24:46.308195+00:00'
---

# Auto-remove section on last entry delete

## Background

BuilderPage.handleUpdateData detects when new data is an empty array AND instance.id is in current instances, then removes the instance (mirrors handleRemoveInstance: marks dirty, sets hasUnsavedChanges). No confirmation modal. SortableAccordionList forwards onSectionEmpty callback; SectionEditorPanel forwards it to editors.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
