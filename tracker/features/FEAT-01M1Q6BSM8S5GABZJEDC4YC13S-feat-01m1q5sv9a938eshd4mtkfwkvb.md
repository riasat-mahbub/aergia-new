---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M1Q6BSM8S5GABZJEDC4YC13S
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
  - FEAT-01M1Q5SV9A938ESHD4MTKFWKVB
AFFECTS: null
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T21:49:27.049045+00:00'
UPDATED_AT: '2026-09-04T21:49:27.049045+00:00'
---

# FEAT-01M1Q5SV9A938ESHD4MTKFWKVB

## Background

Moved the common frontend API/domain modules from web/src/lib/api into web/src/services as the canonical importable service layer: client, auth, cvs, applications, library, profile, render, tailoring, templates, and imports. Updated pages, components, and Zustand stores to import these modules directly. Kept stores, section/editor utilities, validators, security, and short-lived LLM key state in lib. Build, codegen:check, and diff checks pass.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
