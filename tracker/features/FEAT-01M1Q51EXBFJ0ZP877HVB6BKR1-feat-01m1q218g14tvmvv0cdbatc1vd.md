---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M1Q51EXBFJ0ZP877HVB6BKR1
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: Medium
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M1Q218G14TVMVV0CDBATC1VD
AFFECTS: null
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T21:26:19.819253+00:00'
UPDATED_AT: '2026-09-04T21:26:19.819253+00:00'
---

# FEAT-01M1Q218G14TVMVV0CDBATC1VD

## Background

Implemented the direct stage-1 migration: page implementations now live under web/src/app route directories, page-owned components moved beside them, temporary app/router.tsx registers the same URLs for the current Vite runtime, root/dashboard layouts and providers were converted, frontend tests and Vitest configuration/dependencies were removed, and build/codegen:check/diff checks pass. Actual Next runtime cutover remains pending because it requires a deployment/auth topology decision.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
