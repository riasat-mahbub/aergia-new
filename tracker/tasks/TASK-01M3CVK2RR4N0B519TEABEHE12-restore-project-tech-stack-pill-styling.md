---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M3CVK2RR4N0B519TEABEHE12
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS:
- renderer
- pills
- projects
RELATIONS:
  related:
  - BUG-01M2410BFKZBWF86V9WVRFPJRA
AFFECTS:
  files:
  - api/app/services/renderer/html_renderer/html_document.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-25T18:00:10.776566+00:00'
UPDATED_AT: '2026-09-25T18:00:10.776566+00:00'
---

# Restore project tech stack pill styling

## Background

Restored the rounded pill appearance for project technology stacks in the generated CV while retaining the wrapping chip group.

## Investigation

The renderer's current `.f-chip` style had been changed to transparent, square labels. The previous renderer version used a light blue fill and fully rounded corners; project tech fields still use the same wrapping group.

## Decision

Restore the earlier pill styling for rendered project technology values while keeping the wrapping layout.

## Implementation

Restored the pill background, padding, radius, foreground color, and non-underlined link style.

## Verification

`git diff --check` passed. The Impeccable detector returned no findings for the changed renderer file. No tests were run for this CSS-only restoration.

## Follow-up
