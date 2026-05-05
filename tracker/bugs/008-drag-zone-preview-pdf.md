---
ID:             008
TYPE:           bug
NAME:           Drag-to-zone, preview priority, and PDF rendering batch
SUMMARY:        Multiple interrelated bugs in zone assignment, preview rendering, and PDF output
STATUS:         CLOSED
TAGS:           zones, dnd, preview, pdf, batch-fix
LINKS:          fix-commit=3f96b73
---

## Description

A batch of bugs affecting the section-zone merge Phase 6 work:

1. Drag-to-zone: sections dragged into zones did not reliably update placement
2. Preview priority: template-level layout config was not taking priority over
   CV-level config in some cases
3. PDF rendering: exported PDFs did not match the live preview

## Resolution

Fixed the zone assignment logic, preview config prioritization, and PDF
rendering pipeline together in a single batch fix.

### Commit
`3f96b73` — Fix drag-to-zone, preview priority, and PDF export bugs
