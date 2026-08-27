---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNEV
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01M129QBNK54QF2Y9PV8WDKNER
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-11T23:05:40.074678+00:00'
UPDATED_AT: '2026-08-11T23:05:40.074678+00:00'
---

# TASK-01KZSG0GMVHE3XSNN038H9XCFA

## Background

Implemented: _extract_font_dict returns {basefont: family_name}; _infer_font decides bold from family (NotoSans-Bold/SemiBold/Black/Heavy); newline-delimited span grouping replaces coordinate math; _is_candidate_header accepts mixed-case bold headers that match section aliases; _match_section_title requires exact match for single-word aliases (fixes Research Assistant false positive). New tests: tests/test_extract_fonts.py (13), regression tests in test_parser_imports.py. Benchmark CV now detects all 6 sections.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KZSH63FAGEYMNFJ3S7GXBE06 during the schema-4 cutover. -->
