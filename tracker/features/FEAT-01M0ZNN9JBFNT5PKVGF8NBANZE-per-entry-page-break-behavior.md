---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M0ZNN9JBFNT5PKVGF8NBANZE
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- renderer
- page-break
- html
RELATIONS: null
AFFECTS: null
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-26T18:35:00.555332+00:00'
UPDATED_AT: '2026-08-26T18:35:00.555332+00:00'
---

# Per-entry page break behavior

## Background

Move break-inside:avoid from the section wrapper to each <div class="entry">. An overflowing entry moves to the next page on its own instead of dragging the whole section with it. Two-column entries and skill-category entries follow the same rule. heading_keeps_with_first still glues the heading to the first entry. The wire field LayoutHints.keep_together is unchanged in shape; its renderer semantics moved one level down. RendererSupport gains keep_entry_together (BEST_EFFORT) and the renderer emits <!-- best-effort: keep_entry_together --> in the document head.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
