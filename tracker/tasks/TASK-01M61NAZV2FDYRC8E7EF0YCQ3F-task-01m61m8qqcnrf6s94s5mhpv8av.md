---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M61NAZV2FDYRC8E7EF0YCQ3F
TYPE: task
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01M61M8QQCNRF6S94S5MHPV8AV
AFFECTS:
  files:
  - api/app/services/renderer/builders/profile.py
  - api/app/services/renderer/html_renderer/html_document.py
  - api/app/services/renderer/html_renderer/html_entries.py
  - api/app/services/renderer/html_renderer/html_fields.py
  - api/tests/test_builders.py
  - api/tests/test_html_renderer.py
  - api/tests/test_profile_contact_layout.py
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-10-28T16:26:20.898112+00:00'
UPDATED_AT: '2026-10-28T16:26:20.898112+00:00'
---

# Match the print reference contact header

## Background

Refined the initial change against the supplied print PDF: compact uniform contact typography, pipes between all items, no extra social margins, clickable website globe, and browser/PDF geometry regression coverage using the complete reference header. Preserved field ordering, saved alignment and explicit typography controls.

## Investigation


## Decision


## Implementation


## Verification

122 focused tests passed, including geometry checks for the full reference
header on one line in Classic and Minimal browser previews and A4 PDFs.
Verified narrow Modern wrapping and explicit section typography controls.
Visually inspected desktop and narrow captures; design detector found no
issues. `./dev.sh --smoke` passed.

## Follow-up
