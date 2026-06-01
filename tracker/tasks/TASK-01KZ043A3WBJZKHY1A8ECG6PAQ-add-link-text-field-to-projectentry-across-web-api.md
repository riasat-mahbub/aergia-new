---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KZ043A3WBJZKHY1A8ECG6PAQ
TYPE: task
STATUS: IN_PROGRESS
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-02T02:15:56.284848+00:00'
UPDATED_AT: '2026-08-02T02:15:56.284848+00:00'
---

# Add link_text field to ProjectEntry across web + api

## Background

Extend ProjectEntry (web/src/lib/sections/types.ts, api/app/schemas/sections.py) with link_text: str = ""; update Zod validator (web/src/lib/validators/sections.ts); add link_text to seed field lists (api/app/db/seed.py) for projects in three templates; add link_text to sample data (web/src/lib/sections/sampleData.ts). Backend tests + frontend type check must still pass.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
