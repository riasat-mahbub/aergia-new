---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M14NNZ47WQ1MSH7ATA86NKG0
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
  - FEAT-01M14NG6X6KGH2GAVBF651QDFK
AFFECTS: null
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-28T17:11:34.792026+00:00'
UPDATED_AT: '2026-08-28T17:11:34.792026+00:00'
---

# FEAT-01M14NG6X6KGH2GAVBF651QDFK

## Background

Completed UI consistency redesign, including shared palette and favicon, workspace dashboard and CV route split, CV-style application cards/detail actions, consolidated settings, removal of current-password/change-password flow, and library edit mode with field form only. Verification: frontend Vitest 50 files / 317 tests passed; npm run build passed; npm run codegen:check passed; api ruff passed; Python compileall passed. npm run lint remains blocked by existing 75 no-explicit-any errors and 2 hook warnings. Backend pytest was not runnable in the local Python 3.14 environment because the aiosqlite SQLite setup hangs during test database initialization.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
