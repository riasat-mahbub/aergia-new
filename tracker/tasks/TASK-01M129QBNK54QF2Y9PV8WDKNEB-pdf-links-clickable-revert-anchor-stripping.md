---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNEB
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01M129QBNK54QF2Y9PV8WDKNEA
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T20:55:53.935946+00:00'
UPDATED_AT: '2026-08-09T20:55:53.935946+00:00'
---

# PDF links clickable (revert anchor stripping)

## Background

Supersedes TASK-01KZM4MZ7F9QK8JVRGZ8EM4AXQ (link-free PDF). User confirmed the exported PDF must have clickable links. html_to_pdf passes rendered HTML through unchanged; Chromium creates /Subtype /Link + /URI annotations from the real anchors. Verified end to end: generated PDF contains annotations for project/research/cert URLs; pdftotext shows 'Repo \u2197' / 'PDF \u2197'. Preview keeps working new-tab links; arrow stays U+2197. test_render_links.py now guards the preview transform only.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KZM4Z1TFRXWJT4HHP368Y21A during the schema-4 cutover. -->
