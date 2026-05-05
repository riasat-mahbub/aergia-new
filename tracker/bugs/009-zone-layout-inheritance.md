---
ID:             009
TYPE:           bug
NAME:           Zone layout not inherited on CV creation
SUMMARY:        New CVs did not inherit the template's zone layout, leaving unassigned sections
STATUS:         CLOSED
TAGS:           zones, cv-creation, layout, template-inheritance
LINKS:          fix-commit=566ead7
---

## Description

When a new CV was created from the default template, the zone layout was
not inherited. Sections appeared as "unassigned" in the builder UI because
no placement mapping existed at the CV level.

## Resolution

Updated the CV creation flow to copy the template's zone layout and
placement into the new CV's customizations. This ensures new CVs start
with the template's full zone configuration.

### Commit
`566ead7` — Fix zone assignment: inherit template layout on CV creation + draggable unassigned sections
