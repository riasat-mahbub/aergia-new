---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KZM3VN8FHMV98EZHS6Z5RCP8
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T20:36:34.191072+00:00'
UPDATED_AT: '2026-08-09T20:36:34.191072+00:00'
---

# Typography consistency: section-specific header keys + shared grammar

## Background

Shipped with docs/plans/2026-08-09-field-layout-fixes.md Task 6. projects name->project, certifications name->certification, research title->paper; projects tech chips emit uniform key 'tech' so text['tech'] styling applies. Renderer CSS: weight-600 rule covers .f-project/.f-certification/.f-paper; .f-venue/.f-issuer join the 0.875rem line; dead .f-url removed. fieldStyles defs aligned to builder keys (fixes url-vs-link and tech-vs-tech.N mismatches). Builder + renderer consistency tests.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
