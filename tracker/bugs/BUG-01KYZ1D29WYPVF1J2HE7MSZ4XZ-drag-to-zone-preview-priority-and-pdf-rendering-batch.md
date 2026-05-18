---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KYZ1D29WYPVF1J2HE7MSZ4XZ
TYPE: bug
STATUS: DONE
SUMMARY: 'Multiple interrelated bugs in zone assignment, preview rendering, and PDF output'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- zones
- dnd
- preview
- pdf
- batch-fix
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:09:35.804997+00:00'
UPDATED_AT: '2026-08-01T16:09:35.804997+00:00'
---

# Drag-to-zone, preview priority, and PDF rendering batch

## Background

Multiple interrelated bugs in zone assignment, preview rendering, and PDF output

A batch of bugs affecting the section-zone merge Phase 6 work:

1. Drag-to-zone: sections dragged into zones did not reliably update placement
2. Preview priority: template-level layout config was not taking priority over
   CV-level config in some cases
3. PDF rendering: exported PDFs did not match the live preview

*Migrated from SCHEMA 2 entry 008-drag-zone-preview-pdf.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation

Fixed the zone assignment logic, preview config prioritization, and PDF
rendering pipeline together in a single batch fix.

### Commit
`3f96b73` — Fix drag-to-zone, preview priority, and PDF export bugs

## Verification


## Follow-up
