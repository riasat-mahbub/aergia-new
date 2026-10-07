---
SCHEMA: 4
FORMAT: project-tracker
ID: ADR-01M3T5N88RRMTRGSQZCH92QV7Q
TYPE: adr
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
- v10
- contracts
RELATIONS:
  depends_on:
  - TASK-01M3T5N62T6CQ1XVN865DC3DP5
AFFECTS:
  files:
  - docs/tailoring-v10-contract.md
  - api/app/http_schemas/tailoring.py
  - api/app/http_schemas/tailoring_fit_review.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-30T22:06:15.320982+00:00'
UPDATED_AT: '2026-09-30T22:06:15.320982+00:00'
---

# Use ideal first tailoring with advisory independent PDF review

## Background

The user requested preserving the blind ideal CV stage while improving reasonable inference, adding fresh PDF+job fit review, and retaining advisory owner judgment. Protocolv10 freezes these contracts, immutable PDF bindings, relevant snapshot guards, and historical owner review compatibility. Details: docs/tailoring-v10-contract.md.

## Investigation


## Decision

Preserve blind ideal-first composition and ordinary professional inference.
Expose profile, all Library history, and readable source-CV evidence only
after the ideal is complete. Add provider-neutral fresh PDF/job fit review
with exact evaluation/candidate/PDF binding. The report remains advisory;
absence is Not run and an unfavorable verdict never becomes an acceptance
gate. Freeze authoring inputs separately from live target guards. Preserve
historical owner review and introduce explicit saved-revision reevaluation.

## Implementation

P00 freezes DTOs, frontend types, error codes, and the storage/service
blueprint in docs/tailoring-v10-contract.md. Subsequent packets implement
those behaviors on feature/tailoring-v10. This ADR records the chosen design;
the aggregate implementation feature remains IN_PROGRESS.

## Verification

Six P00 synthetic contract tests and frontend typecheck passed. Protocol-v10
runtime and semantic workflow verification remain the responsibility of P13.

## Follow-up
