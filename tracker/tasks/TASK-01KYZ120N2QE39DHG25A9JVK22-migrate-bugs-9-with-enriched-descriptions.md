---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KYZ120N2QE39DHG25A9JVK22
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
CREATED_AT: '2026-08-01T16:03:33.666933+00:00'
UPDATED_AT: '2026-08-01T16:03:33.666933+00:00'
---

# Migrate bugs (9) with enriched descriptions

## Background

For each old bug file run `tracker new bug "<name>" --status DONE --tags "<tags>" --description "<composed>"`; composed Background = old SUMMARY + old Description body + provenance line; set frontmatter SUMMARY; move old Resolution content (commit hashes) into new ## Implementation; record old→new ID mapping in scratch tracker/_migration-map.md. Verify: 9 new BUG-*.md; every file has "Migrated from" + "SUMMARY:"; tracker validate shows no bug-folder errors.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
