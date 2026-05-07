---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KYZ1D1Y3TJ8WB8YAHDYF15YN
TYPE: bug
STATUS: DONE
SUMMARY: 'Zone widths within a row could exceed or fall short of 100%, breaking the layout'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- zones
- layout
- width
- normalization
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:09:35.427727+00:00'
UPDATED_AT: '2026-08-01T16:09:35.427727+00:00'
---

# Zone widths not summing to 100%

## Background

Zone widths within a row could exceed or fall short of 100%, breaking the layout

Zone widths within each row were not automatically normalized to sum to
100%. When users added or resized zones, the total width could exceed 100%
(causing overflow/scroll) or fall short of 100% (leaving empty space).

*Migrated from SCHEMA 2 entry 003-zone-widths-not-normalized.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation

Added per-row width normalization logic in `normalizeWidths()` and
`normalizeAllZones()` helper functions. Zone widths in the same row are
now normalized to proportionally scale when a zone is added or resized.
The normalization is applied in all zone mutation handlers.

### Commits
`d0f427a` — fix: normalize zone widths to always sum to 100%
`9b2b54d` — Fixed zone width issues

## Verification


## Follow-up
