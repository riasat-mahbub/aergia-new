---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M37MD9KTHMPW4VJQWY6PMB1R
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
  - FEAT-01M37J1TTVXG3M8YJPYHSP6C40
AFFECTS:
  files:
  - api/app/services/candidate_evidence.py
  - api/app/services/requirement_extractor.py
  - api/app/services/tailoring.py
  - api/tests/test_candidate_evidence.py
  - api/tests/test_requirement_extractor.py
  - api/tests/test_tailoring.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-23T17:18:28.986745+00:00'
UPDATED_AT: '2026-09-23T17:18:28.986745+00:00'
---

# FEAT-01M37J1TTVXG3M8YJPYHSP6C40

## Background

Validate whether the v6 candidate evidence layer can supply source-grounded propositions for fresh composition using the configured production GLiNER2.5-small model. Keep v5 available as the Convverge comparison baseline.

## Investigation

Ran the pinned `fastino/gliner2.5-small-v1` revision offline against the Convverge session’s exact 21-entry Library snapshot, including 11 narrative fields. It emitted 3 `evidence_claim` spans across 3 research records. None was a complete meaningful action proposition; experience and project claim recall was zero. All 3 spans matched their exact source ranges and content hashes, but they were noun fragments. Lower confidence thresholds and alternate action/task/activity label descriptions did not recover the missing claims.

Six equivalent Brain Station source forms produced claim counts `0/1/0/0/0/0`; the one output was the fragment `application reliability`. The other label spans were mostly technologies and artifacts, with no claim links for deployment, testing, development, or collaboration. Structured identity and dates remained in the composer projection.

The accepted v5 Convverge draft retains four Brain Station bullets in one-to-one topical groups: development/Agile, testing, deployment, and plugins/HTML parsing. It reorders those groups relative to both the Library and saved prior CV, drops the reliability/technical-debt outcome from the testing group, and places source-supported Agile/Scrum in the development group. The v5 profile also adds an interest statement about Microsoft cloud/Power Platform that is not explicit in the Library; it does not claim Azure experience. The Library has no explicit documentation, Azure, or Microsoft text, so those terms cannot be restored from its candidate evidence. The v6 composer projection has zero Brain Station claims, so it cannot produce a fact-grounded Brain Station composition; no v6 candidate is claimed. The stored v5 scanner comparison shows Job Fit `0.5030 → 0.5314`, keyword visibility unchanged at `0.6313`, documentation and Azure remaining partial, and no requirement regressions.

## Decision

GLiNER alone is insufficient for proposition extraction. Preserve it for explicit concept spans and provenance, and evaluate a job-blind isolated LLM fallback for narrative sources whose action claims are absent or invalid. The fallback would cover most experience and project descriptions in this sample, so this is not a rare ambiguous-case path. The evidence schema can still hold propositions and local relations; the observed failure is primarily the GLiNER-only extraction method.

## Implementation

No extraction behavior was changed during this validation. Real-model outputs and candidate data remain in a local, permission-restricted audit directory rather than the repository.

## Verification

Focused candidate-evidence, requirement-extraction, and tailoring tests: 26 passed. The real-model provenance audit passed for all 3 emitted claims. `tracker rebuild` completed; `tracker validate` reported 0 errors and 7 pre-existing supersession-fork warnings.

## Follow-up

Before late Library recovery or regression review, evaluate an isolated, job-blind proposition-extraction fallback against the audited sources and the split/merge/order/paraphrase cases. Re-run the Convverge comparison only after the v6 composer receives complete, useful Brain Station evidence. Keep page optimization and broader v5/v6 quality evaluation deferred until fresh composition is possible.
