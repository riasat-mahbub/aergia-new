---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M182ASVXYVVW5BGP5MZAGH0H
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01M17Z1JZ4485PF7PXCZSVBVSG
AFFECTS:
  files:
  - api/scripts/gliner2_spike.py
  - api/scripts/gliner2_spike_lib.py
  - api/scripts/gliner2_jobs.json
  - api/scripts/run_gliner2_spike_docker.sh
  - api/Dockerfile.gliner2-spike
  - api/tests/test_gliner2_spike.py
  - docs/plans/2026-08-29-gliner2.5-spike.md
LINKS:
  plan: docs/plans/2026-08-29-gliner2.5-spike.md
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-30T00:50:23.741264+00:00'
UPDATED_AT: '2026-08-30T00:50:23.741264+00:00'
---

# TASK-01M17Z1JZ4485PF7PXCZSVBVSG

## Background

Completed isolated GLiNER2.5 spike. Small passed at 2 GiB but OOMed at 1 GiB; base OOMed at 2 GiB and showed no quality gain. Retain requirement-v2 for production and evaluate small only as a future semantic-assist candidate on a larger real-posting corpus.

## Investigation

The production path was not changed. The spike adapts the proposed
Requirement contract around source text/spans, type, tri-state importance,
concepts, deterministic constraints, confidence, and extractor metadata.
GLiNER2.5-small-v1 and -base-v1 were loaded through AutoExtractor in a
production-derived Docker image. The comparison used four evaluated fixture
postings plus a 4,160-word long-document stress case.

Small achieved 90.9% precision and 52.6% recall alone; the comparison-only
small+requirement-v2 merge achieved 72.0% precision and 94.7% recall. Base
achieved 83.3% precision and 26.3% recall alone, with no quality advantage.
Small OOMed under a hard 1 GiB limit and passed at 2 GiB; base OOMed at 2 GiB
and required 3 GiB to complete. Warm short extraction was approximately
0.36–0.51 seconds for small and 1.13–1.32 seconds for base on one vCPU.

## Decision

Retain requirement-v2 for production with targeted improvements. Keep
GLiNER2.5-small as a candidate semantic-assist extractor for a larger labeled
real-posting evaluation. Do not ship base for the documented low-cost target.
If production adoption proceeds, budget at least 3 GiB RAM for small (2 vCPUs
preferred for concurrency) and retain deterministic authority for explicit
importance and constraints.

## Implementation

Added isolated contract/adapter code, deterministic enrichment and comparison
logic, representative fixtures, a CPU-only production-derived Docker
benchmark image/runner, and contract tests. No Library, matcher, CV,
frontend, SQLite, or public API code was modified.

## Verification

`PYTHONPATH=api api/.venv/bin/pytest --noconftest -q
api/tests/test_gliner2_spike.py` passed (7 tests). Ruff passed for all new
Python files and `bash -n` passed for the Docker runner. Docker runs measured
the small and base checkpoints under 1/2/3/4 GiB limits and exercised the
384-word/64-word-overlap long-document path.

## Follow-up

Build a larger labeled corpus from real postings, rerun the small checkpoint
with exact revisions, and test model-plus-Chromium concurrency before any
production lifecycle, fallback, shadow rollout, or persistence work.
