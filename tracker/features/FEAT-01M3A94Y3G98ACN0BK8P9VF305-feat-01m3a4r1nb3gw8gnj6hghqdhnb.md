---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M3A94Y3G98ACN0BK8P9VF305
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M3A4R1NB3GW8GNJ6HGHQDHNB
AFFECTS:
  files:
  - api/app/http_schemas/tailoring.py
  - api/app/http_schemas/tailoring_evaluation.py
  - api/app/services/tailoring.py
  - api/app/services/tailoring_evaluation.py
  - api/app/services/tailoring_opportunities.py
  - api/tests/test_tailoring.py
  - api/tests/test_tailoring_contracts.py
  - api/tests/test_tailoring_evaluation.py
  - api/tests/test_tailoring_opportunities.py
  - docs/matching-and-tailoring.md
  - tailoring-skill/AGENTS.md
  - tailoring-skill/README.md
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/references/claim-verification.schema.json
  - tailoring-skill/skills/aergia-tailor/references/editorial-review.schema.json
  - tailoring-skill/skills/aergia-tailor/references/inference-notes.schema.json
  - tailoring-skill/skills/aergia-tailor/references/natural-writing.md
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - tailoring-skill/skills/aergia-tailor/scripts/validate-candidate.mjs
  - tailoring-skill/skills/aergia-tailor/scripts/validate-editorial-review.mjs
  - tailoring-skill/skills/aergia-tailor/scripts/verify-claims.mjs
  - tailoring-skill/tests/candidate.test.mjs
  - tailoring-skill/tests/editorial-review.test.mjs
  - tailoring-skill/tests/session.test.mjs
  - tailoring-skill/tests/verify-claims.test.mjs
  - web/src/features/applications/components/detail/ApplicationCvPanel.tsx
  - web/src/features/tailoring/types/index.ts
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-24T17:59:24.017017+00:00'
UPDATED_AT: '2026-09-24T17:59:24.017017+00:00'
---

# FEAT-01M3A4R1NB3GW8GNJ6HGHQDHNB

## Background

Updated the protocol-v8 tailoring loop to prioritize target relevance and ordinary professional inference. Removed claim-verification and inference-note submission gates, the critic workflow, and CandidateEvidence-based unsupported-skill risk suppression. Submission remains bound to the selected evaluation_id and candidate_hash; opportunity retrieval now favors required target priorities and reads original Library narratives independently of semantic freshness.

## Investigation


## Decision


## Implementation

- Replaced evidence-confidence guidance with relevance-first target selection,
  broad professional inference, aggressive employer-language reframing, and a
  narrow fixed-fact boundary.
- Removed the claim verifier, its schema, candidate-input hash output,
  inference-note contracts/UI, and critic metrics/workflow.
- Kept CandidateEvidence and semantic indexing as retrieval aids; removed the
  unsupported-skill fabrication finding and ranked opportunity sources by job
  requirement priority while retaining current Library narratives.
- Preserved v8 selection binding through `candidate_hash` and `evaluation_id`.


## Verification

- `node --test tailoring-skill/tests/*.test.mjs` passed.
- Focused tailoring API tests: 33 passed, 1 skipped.
- `cd web && npm run typecheck` passed.
- `git diff --check` passed.


## Follow-up
