---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KYZ120MTE8HW4RXRYXSYDJ3X
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
CREATED_AT: '2026-08-01T16:03:33.658375+00:00'
UPDATED_AT: '2026-08-01T16:03:33.658375+00:00'
---

# Scaffold new-format support files

## Background

Create tracker/.gitignore (graph.json), replace tracker/_template.md with SCHEMA 3 template, add .git/hooks/post-merge + post-checkout (tracker rebuild on git events; chmod +x). Verify: cat tracker/.gitignore shows graph.json; head -3 tracker/_template.md shows SCHEMA: 3; post-merge hook exists and is executable.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
