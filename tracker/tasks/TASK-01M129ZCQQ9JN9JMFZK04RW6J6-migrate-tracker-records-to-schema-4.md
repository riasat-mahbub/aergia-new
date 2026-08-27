---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129ZCQQ9JN9JMFZK04RW6J6
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- tracker
- migration
- schema-4
RELATIONS: null
AFFECTS: null
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-27T19:08:31.863781+00:00'
UPDATED_AT: '2026-08-27T19:08:31.863781+00:00'
---

# Migrate tracker records to schema 4

## Background

Migrated all 274 SCHEMA 3 records to SCHEMA 4 with fresh ULIDs. Converted epic and doc records to feature and task records, normalized stale filename-style relation targets, replaced tracks with related, linearized supersedes chains, and marked the confirmed duplicate record as DUPLICATE. Retained all entry bodies and provenance comments. Verified 324 entries with no missing relation targets, supersedes forks, multi-parent supersedes, cycles, malformed metadata, or validator errors. Pre-cutover backup: /tmp/aergia-tracker-pre-chain-cutover-20260827T185627Z.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
