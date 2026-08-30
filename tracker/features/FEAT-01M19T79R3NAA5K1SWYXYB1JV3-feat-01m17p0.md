---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M19T79R3NAA5K1SWYXYB1JV3
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS:
- relevance
- requirements
- testing
RELATIONS:
  supersedes:
  - FEAT-01M17P5H9FQ9A2YQFZEFP3ECGZ
AFFECTS:
  files:
  - api/app/services/requirement_extractor.py
  - api/app/services/relevance.py
  - api/app/services/relevance_taxonomy.py
  - api/tests/test_requirement_extractor.py
  - api/tests/test_requirement_relevance.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-30T17:07:09.187523+00:00'
UPDATED_AT: '2026-08-30T17:07:09.187523+00:00'
---

# FEAT-01M17P0

## Background

Implemented GLiNER-bounded deterministic enrichment and relevance scoring: decimal/range years with partial under-minimum credit, degree/certification aliases, explicit AND/OR concept groups, local context attachment, provenance preservation, and demonstrated evidence weighting (projects > experience > skills list). Added Affirm-style, empty-GLiNER, provenance, partial-match, logical-group, and evidence-strength tests. Focused extractor/relevance checks pass; full pytest bootstrap remains blocked because Alembic hangs on a fresh temporary SQLite database before collection.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
