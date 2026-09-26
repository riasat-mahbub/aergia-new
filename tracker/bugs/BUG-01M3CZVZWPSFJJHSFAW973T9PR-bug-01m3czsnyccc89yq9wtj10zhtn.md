---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3CZVZWPSFJJHSFAW973T9PR
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: Medium
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01M3CZSNYCCC89YQ9WTJ10ZHTN
  depends_on:
  - BUG-01M3CXFAPJGQEAFQ07T3X5FG3C
AFFECTS:
  files:
  - api/app/scanner/extraction.py
  - api/app/services/requirement_extractor.py
  - api/tests/test_scanner_extraction.py
  - api/tests/test_scanner_application_api.py
  - api/tests/test_scanner_backfill.py
  - api/tests/test_scanner_independent_analyses.py
  - api/tests/test_tailoring.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-25T19:14:57.046246+00:00'
UPDATED_AT: '2026-09-25T19:14:57.046246+00:00'
---

# BUG-01M3CZSNYCCC89YQ9WTJ10ZHTN

## Background

Removed posting-specific phrase guards; candidate and section evidence now gate model spans and broad lexical cues, with application actions excluded from CV job fit. Extractor v11 verified by focused, broad, and smoke checks.

## Investigation

Broad `you can`, `must`, and `interest in` matches admitted employer and
application prose. Model requirement spans and the unknown-section fallback
could independently promote the same copy. The previous phrase list hid the
symptoms. Full source and raw model spans for the user's scan were unavailable.


## Decision

Candidate evidence must come from a genuine sentence directive or candidate
section; a model label alone is corroboration. Application steps are process
actions, not CV match criteria.


## Implementation

Removed phrase-specific boilerplate guards, narrowed directed-language cues,
made non-candidate section context authoritative except for genuine candidate
obligations, and clarified the model label. Extractor v11 invalidates old scans.


## Verification

74 focused extraction/scoring tests passed; 237 scanner/tailoring tests passed
with the pre-existing skill-bundle assertion deselected. After a final small
application-process grammar refinement, 57 extraction/fixture tests and the
repository smoke gate passed. Ruff, `git diff --check`, and tracker validation
passed. The detailed investigation is in the previous chain revision.


## Follow-up

Rescan the Scotiabank application to replace its stored v10 result.
