---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M2ZTT35MHHFNVWX3D9R065GE
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS:
  files:
  - api/app/services/renderer/html_values.py
  - api/tests/test_html_renderer.py
  - web/src/styles/tokens.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-20T16:36:24.372613+00:00'
UPDATED_AT: '2026-09-20T16:36:24.372613+00:00'
---

# Make tight section spacing more compact

## Background

The Tight section-spacing token resolved to 12px, leaving excessive gaps in compact sections such as Skills. Reduce its renderer value to 4px and keep the inspector spacing indicator in sync.

## Investigation

The renderer resolved the section spacing token `tight` to 12px. The section
spacing controls and their live indicator use the same scale, so both values
need to change together.

## Decision

Keep the existing token vocabulary and lower the `tight` spacing value to
4px. This also updates other section spacing controls that use `tight`;
template padding tokens are independent and remain unchanged.

## Implementation

Updated the HTML spacing map and the inspector indicator to 4px, and adjusted
the renderer assertion for tight field spacing.

## Verification

Tests were not run.

## Follow-up
