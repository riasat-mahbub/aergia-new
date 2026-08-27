---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M129QBNK54QF2Y9PV8WDKN75
TYPE: bug
STATUS: DONE
SUMMARY: New CVs did not inherit the template's zone layout, leaving unassigned sections
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- zones
- cv-creation
- layout
- template-inheritance
RELATIONS:
  related:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN8E
  - FEAT-01M129QBNK54QF2Y9PV8WDKN8K
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:09:35.876608+00:00'
UPDATED_AT: '2026-08-01T16:09:35.876608+00:00'
---

# Zone layout not inherited on CV creation

## Background

New CVs did not inherit the template's zone layout, leaving unassigned sections

When a new CV was created from the default template, the zone layout was
not inherited. Sections appeared as "unassigned" in the builder UI because
no placement mapping existed at the CV level.

*Migrated from SCHEMA 2 entry 009-zone-layout-inheritance.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation

Updated the CV creation flow to copy the template's zone layout and
placement into the new CV's customizations. This ensures new CVs start
with the template's full zone configuration.

### Commit
`566ead7` — Fix zone assignment: inherit template layout on CV creation + draggable unassigned sections

## Verification


## Follow-up

<!-- Migrated from BUG-01KYZ1D2C4C1P0R85P0J15G72D during the schema-4 cutover. -->
