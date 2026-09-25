---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M38W5XGNVE9ZEW3S7EHTTYX9
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS:
- candidate-index
- tailoring
- job-fit
RELATIONS: null
AFFECTS: null
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-24T04:53:30.261403+00:00'
UPDATED_AT: '2026-09-24T04:53:30.261403+00:00'
---

# Persistent candidate index and holistic tailoring v7

## Background

Replaced per-session candidate evidence rebuilding with a persistent deterministic index and fingerprinted semantic records per Library narrative source. Library mutations now atomically maintain stable row IDs and deterministic source terms while making changed semantic records stale. Protocol v7 refreshes only bounded stale batches through a job-blind isolated worker, validates results per source, rejects stale writes, and continues with deterministic retrieval when enrichment fails. Job Fit remains based on the linked CV and uses job-fit-v3. Tailoring retrieves bounded original narratives, instructs holistic re-authoring, performs strict claim verification, uses a lazy critic only for uncertainty, and keeps the normal revision loop bounded. Validation: API 781 passed and 2 skipped excluding the sandbox-blocked PDF smoke; PDF smoke passes with Chromium outside the sandbox; repository dev smoke, frontend lint/typecheck/architecture/codegen checks, Ruff, and tailoring-skill Node tests pass.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
