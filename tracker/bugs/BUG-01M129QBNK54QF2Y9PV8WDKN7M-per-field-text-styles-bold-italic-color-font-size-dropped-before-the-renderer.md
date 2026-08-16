---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M129QBNK54QF2Y9PV8WDKN7M
TYPE: bug
STATUS: PROPOSED
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T18:15:04.267182+00:00'
UPDATED_AT: '2026-08-09T18:15:04.267182+00:00'
---

# Per-field text styles (bold/italic/color/font-size) dropped before the renderer

## Background

The customize panel writes SectionInstanceStyle.text[field_key] and customizations.per_section[id].text[field_key], but build_document copied only policy/subsection/layout onto the Section AST node and builders created TextRun objects with no style, so bold/italic/color/font-size never reached the preview or PDF (the renderer reads TextRun.style). Reproduced via API: PATCH a CV with style.text and the preview HTML had no font-weight/color/font-size/italic declarations. Fix: apply_field_text_styles() bridges SectionInstanceStyle.text onto the field runs in build_document, and the resolver's per-section overlay merges override.text the same way.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from BUG-01KZKVRJAB2HDEAKD286D6K6JJ during the schema-4 cutover. -->
