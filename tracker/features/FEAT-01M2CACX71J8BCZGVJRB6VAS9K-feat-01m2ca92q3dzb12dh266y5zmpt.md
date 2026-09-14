---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2CACX71J8BCZGVJRB6VAS9K
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M2CA92Q3DZB12DH266Y5ZMPT
AFFECTS:
  files:
  - api/app/http_schemas/tailoring.py
  - api/app/services/quality.py
  - api/app/services/tailoring.py
  - api/tests/test_quality.py
  - api/tests/test_tailoring.py
  - api/tests/test_tailoring_contracts.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/references/critique.schema.json
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - tailoring-skill/skills/aergia-tailor/scripts/validate-candidate.mjs
  - tailoring-skill/skills/aergia-tailor/scripts/validate-critique.mjs
  - tailoring-skill/tests/candidate.test.mjs
  - tailoring-skill/tests/critique.test.mjs
  - tailoring-skill/tests/session.test.mjs
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-13T02:44:00.865258+00:00'
UPDATED_AT: '2026-09-13T02:44:00.865258+00:00'
---

# FEAT-01M2CA92Q3DZB12DH266Y5ZMPT

## Background

The bullet-balance wording change is complete and tracked separately; the broader critique-loop work remains open pending its documented end-to-end API/ASGI verification follow-up.

## Investigation


## Decision


## Implementation

The related bullet-balance guidance is complete; this feature remains in
progress for its existing verification follow-up.


## Verification

The focused tailoring-skill Node test suite passes. The full API/ASGI follow-up
remains documented in the feature history.


## Follow-up
