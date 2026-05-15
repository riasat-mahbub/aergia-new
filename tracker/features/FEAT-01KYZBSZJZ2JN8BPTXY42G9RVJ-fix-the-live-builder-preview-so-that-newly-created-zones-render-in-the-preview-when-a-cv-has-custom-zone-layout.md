---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KYZBSZJZ2JN8BPTXY42G9RVJ
TYPE: feature
STATUS: PLANNED
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- plan
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T19:11:24.767837+00:00'
UPDATED_AT: '2026-08-01T19:11:24.767837+00:00'
---

# Fix the live builder preview so that newly-created zones render in the preview when a CV has custom zone layout.

## Background

Fix the live builder preview so that newly-created zones render in the preview when a CV has custom zone layout. Root cause: build_ir derives the zones to render from manifest.zones (template defaults) instead of manifest.layout_config.zones (the CV's live zones). The builder's live /render/html path passes zones only via layout_config.zones, so new zones never render.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
