---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KZSG0GMVHE3XSNN038H9XCFA
TYPE: task
STATUS: PROPOSED
PRIORITY: High
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- parser
- fix
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-11T22:45:08.379447+00:00'
UPDATED_AT: '2026-08-11T22:45:08.379447+00:00'
---

# pdf-parser: font-name-based bold inference

## Background

Task 1 of plan docs/plans/2026-08-11-pdf-parser-resilience.md. Replace the line == line.upper() bold heuristic in _infer_font with a font-name-based check wired from the page's /Resources/Font dictionary. Fix _extract_font_dict to return {basefont: family_name} (Type0 subsets have no size in the name). Drop the ALL-CAPS text heuristic. New tests in api/tests/test_extract_fonts.py.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
