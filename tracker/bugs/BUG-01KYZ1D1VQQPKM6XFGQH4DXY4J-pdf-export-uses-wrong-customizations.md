---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KYZ1D1VQQPKM6XFGQH4DXY4J
TYPE: bug
STATUS: DONE
SUMMARY: 'PDF export applied CV-level customizations instead of system template defaults for system templates'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- pdf
- template
- customizations
- system-template
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:09:35.351182+00:00'
UPDATED_AT: '2026-08-01T16:09:35.351182+00:00'
---

# PDF export uses wrong customizations

## Background

PDF export applied CV-level customizations instead of system template defaults for system templates

When using system templates (Modern, Classic, Minimal), the PDF export
incorrectly used the user's CV customizations for the layout instead of
the system template's default layout. This caused exported PDFs to have
broken layouts.

*Migrated from SCHEMA 2 entry 002-pdf-wrong-customizations.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation

Updated the PDF service to use the system template's layout configuration
when the CV uses a system template, rather than relying on CV-level
customizations.

### Commit
`023263e` — fix: PDF export uses CV customizations layout for system templates

## Verification


## Follow-up
