---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN89
TYPE: feature
STATUS: DONE
SUMMARY: Refactored from one-instance-per-type to multiple named instances per section
  type
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- sections
- instances
- phase-5
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:11:57.540544+00:00'
UPDATED_AT: '2026-08-01T16:11:57.540544+00:00'
---

# Section instance model (multiple per type)

## Background

Refactored from one-instance-per-type to multiple named instances per section type

Architectural refactor replacing the single-instance-per-type model with
a `SectionInstance[]` array:
- Each instance has `id`, `type`, `title`, `enabled`, `data`
- Multiple instances of the same type allowed (e.g. two Experience sections)
- Instance CRUD: add, remove, reorder, toggle, rename
- New CVs start with one enabled Profile instance
- Backend stores as JSONB in `cvs.sections`
- Frontend cvStore updated with instance-focused handlers

*Migrated from SCHEMA 2 entry 009-section-instance-model.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification

All Phase 5 tasks complete including T45-T46 tests.

## Follow-up

<!-- Migrated from FEAT-01KYZ1HCQ40GHEYZA567JRGTKV during the schema-4 cutover. -->
