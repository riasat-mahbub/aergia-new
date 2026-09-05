---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1QF6Z496YPB69XH7JVDAXRR
TYPE: task
STATUS: IN_PROGRESS
PRIORITY: Medium
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS:
- refactor
- frontend
- architecture
RELATIONS: null
AFFECTS: null
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-05T00:24:06.025332+00:00'
UPDATED_AT: '2026-09-05T00:24:06.025332+00:00'
---

# Reorganize shared CV section editors and profile editing

## Background

Refactor the frontend module boundaries: decouple reusable section editors from library-specific actions; move shared React editors and primitives under components/common/section-editors; move pure section utilities to responsibility-based lib modules; keep profile data in the shared profile store while extracting a controlled UserProfileEditor and page-specific profile cards; replace the loose section registry with typed definitions and registry; preserve builder, settings, and library behavior and verify with frontend gates.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
