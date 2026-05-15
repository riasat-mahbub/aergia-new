---
ID:             002
TYPE:           bug
NAME:           PDF export uses wrong customizations
SUMMARY:        PDF export applied CV-level customizations instead of system template defaults for system templates
STATUS:         CLOSED
TAGS:           pdf, template, customizations, system-template
LINKS:          fix-commit=023263e
---

## Description

When using system templates (Modern, Classic, Minimal), the PDF export
incorrectly used the user's CV customizations for the layout instead of
the system template's default layout. This caused exported PDFs to have
broken layouts.

## Resolution

Updated the PDF service to use the system template's layout configuration
when the CV uses a system template, rather than relying on CV-level
customizations.

### Commit
`023263e` — fix: PDF export uses CV customizations layout for system templates
