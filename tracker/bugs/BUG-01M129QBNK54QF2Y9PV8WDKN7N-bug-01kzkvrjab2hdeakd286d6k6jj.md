---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M129QBNK54QF2Y9PV8WDKN7N
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01M129QBNK54QF2Y9PV8WDKN7M
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T18:15:11.073324+00:00'
UPDATED_AT: '2026-08-09T18:15:11.073324+00:00'
---

# BUG-01KZKVRJAB2HDEAKD286D6K6JJ

## Background

Fixed: apply_field_text_styles() attaches SectionInstanceStyle.text to field runs in build_document; resolve's _apply_section_overlay merges override.text onto runs for the per_section path. Verified live (preview + PDF): bold font-weight:700, color:#ff0000, font-size:1.25rem, font-style:italic all render. Tests: test_build_document_attaches_per_field_styles_to_runs, test_per_section_text_overlay_applies_to_runs (api), CustomizePanel field-style tests (web).

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from BUG-01KZKVRRZ15Y87F0QDM174JRZB during the schema-4 cutover. -->
