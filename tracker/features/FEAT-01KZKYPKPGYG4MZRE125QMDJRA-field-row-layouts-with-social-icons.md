---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KZKYPKPGYG4MZRE125QMDJRA
TYPE: feature
STATUS: PROPOSED
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - EPIC-01KZCCC3MTXDGPY31H06NFYP1Q
AFFECTS:
  files:
  - api/app/schema/models.py
  - api/app/services/renderer/builders/*.py
  - api/app/services/renderer/html.py
  - web/src/generated/schema.ts
  - api/tests/test_builders.py
  - api/tests/test_html_renderer.py
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T19:06:25.872606+00:00'
UPDATED_AT: '2026-08-09T19:06:25.872606+00:00'
---

# Field-row layouts with social icons

## Background

Restore sophisticated field layouts in the HTML-first renderer (Option A): FieldBlock gains group + icon; builders emit per-type row groups (profile: main/subtitle/contact/social/summary; others: header/meta/body); the renderer wraps same-group fields in .field-row and draws social icons from a renderer icon table. Fixes the flat back-to-back field rendering and missing social icons.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
