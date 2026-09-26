---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M3CZSNYCCC89YQ9WTJ10ZHTN
TYPE: bug
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: Medium
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01M3CXYKKYJYTK8YCANRHP3CZA
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
CREATED_AT: '2026-09-25T19:13:41.324864+00:00'
UPDATED_AT: '2026-09-25T19:13:41.324864+00:00'
---

# BUG-01M3CXYKKYJYTK8YCANRHP3CZA

## Background

Prior v10 fix depended on posting-specific boilerplate phrases; root-cause correction replaces those guards with candidate-evidence and section-context rules.

## Investigation

The raw model output for the original Scotiabank scan is unavailable, so its
exact span labels and section headings cannot be asserted. The source code
provided two independent false-positive paths: `_DIRECTED_PATTERNS` accepted
bare `you can`, `must`, and `interest in` even inside employer and application
prose; a `candidate_requirement` model span also contributed enough confidence
to admit an unknown-section sentence on its own. The classifier's unknown
fallback labelled such sentences as candidate requirements. In a known
non-candidate section, a model span bypassed the section veto and its score
outweighed the weak section penalty. Importance then marked `must apply` as
required. The prior fix masked examples with phrase-specific regexes.


## Decision

Require independent sentence or candidate-section evidence before a model span
can promote text. Treat application steps as process actions, and make known
employer sections authoritative unless a genuine candidate obligation or job
duty appears. Use grammatical subject and action categories rather than
posting-specific boilerplate text.


## Implementation

Removed the phrase-specific boilerplate and company-copy lists. Narrowed
candidate-directed cues, added a process-action gate, retained explicit
qualifications and duties in mixed sections, and clarified the model label.
Extractor contract v11 makes stored analyses stale for rescanning.


## Verification

Exact Scotiabank and Ericsson examples, varied employer/process copy, and
genuine qualifications are covered by extraction tests. Focused extraction
and scoring: 74 passed. Scanner/tailoring suite: 237 passed with one known
pre-existing skill-bundle test deselected. `./dev.sh --smoke` passed, including
the live gateway. `git diff --check` and Ruff passed.


## Follow-up

The original Scotiabank posting and model spans were not available locally;
rescan its application to replace the stored v10 analysis and inspect any
remaining ambiguous source sentences.
