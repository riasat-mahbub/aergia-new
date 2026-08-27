---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNAP
TYPE: task
STATUS: PLANNED
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- plan
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:03:33.716309+00:00'
UPDATED_AT: '2026-08-01T16:03:33.716309+00:00'
---

# Migrate issues (7) with enriched descriptions

## Background

Map tracker/issues/ → decisions/ (3 ADRs: 003/004/007, --status DONE), tasks/ (001 test suite PROPOSED, 002 SECRET_KEY DONE, 005 npm vulns DONE), docs/ (006 template guide PROPOSED). ADR Background = SUMMARY + Context body; ### Decision + ### Consequences → ## Decision; ### Changes → ## Implementation. Verify: 3 ADR-* + 3 TASK-* + 1 DOC-*; grep -rL "Migrated from" prints nothing; tracker validate only reports remaining old issues/ files.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KYZ120PMXA3W46HFNXA3P5A1 during the schema-4 cutover. -->
