---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M387M2YAJAB397XT11N1T0N1
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS:
  files:
  - benchmarks/job-requirements/current-architecture.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-23T22:54:14.474868+00:00'
UPDATED_AT: '2026-09-23T22:54:14.474868+00:00'
---

# Document current scanner architecture baseline

## Background

Added benchmarks/job-requirements/current-architecture.md as a read-only factual baseline. No production code changed and no tests or model inference were run. Covers the separate scanner and legacy relevance paths; GLiNER2.5-small and deterministic parsing; v6 CandidateEvidence/provenance/projection; matching/status/scoring; scanner outputs; v5/v6 context isolation; fixtures and known gaps.

## Investigation

Inspected the scanner and legacy requirement extraction paths, shared GLiNER runtime, candidate evidence contracts, matching/scoring, scanner output generation, tests/fixtures, and v5/v6 session flow on `master`.

## Decision

Record implementation behavior and confirmed boundaries only. Do not change production code or select a replacement model.

## Implementation

Added `benchmarks/job-requirements/current-architecture.md`, including job, candidate, and match/scoring diagrams; data-model conversions; the requested known-case audit; discrepancy classifications; and test coverage gaps.

## Verification

Read-only source inspection on `master` at `4db4a21`. No tests or model inference were run because the deliverable is a factual architecture report.

## Follow-up

Use this baseline in the next semantic interpretation and matching design phase.
