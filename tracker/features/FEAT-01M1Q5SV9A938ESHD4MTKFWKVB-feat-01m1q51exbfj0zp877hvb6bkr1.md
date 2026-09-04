---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M1Q5SV9A938ESHD4MTKFWKVB
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
  - FEAT-01M1Q51EXBFJ0ZP877HVB6BKR1
AFFECTS: null
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T21:39:38.922902+00:00'
UPDATED_AT: '2026-09-04T21:39:38.922902+00:00'
---

# FEAT-01M1Q51EXBFJ0ZP877HVB6BKR1

## Background

Moved the Builder out of the dashboard URL namespace. Its implementation and page-owned components now live under web/src/app/builder/[id], the Vite registry exposes /builder/:id while retaining the authenticated dashboard shell, and all internal Builder links were updated from /dashboard/builder/:id. Build, codegen:check, and diff checks pass.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
