---
ID:             003
TYPE:           bug
NAME:           Zone widths not summing to 100%
SUMMARY:        Zone widths within a row could exceed or fall short of 100%, breaking the layout
STATUS:         CLOSED
TAGS:           zones, layout, width, normalization
LINKS:          fix-commit=d0f427a, fix-commit=9b2b54d
---

## Description

Zone widths within each row were not automatically normalized to sum to
100%. When users added or resized zones, the total width could exceed 100%
(causing overflow/scroll) or fall short of 100% (leaving empty space).

## Resolution

Added per-row width normalization logic in `normalizeWidths()` and
`normalizeAllZones()` helper functions. Zone widths in the same row are
now normalized to proportionally scale when a zone is added or resized.
The normalization is applied in all zone mutation handlers.

### Commits
`d0f427a` — fix: normalize zone widths to always sum to 100%
`9b2b54d` — Fixed zone width issues
