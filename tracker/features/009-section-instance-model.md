---
ID:             009
TYPE:           feature
NAME:           Section instance model (multiple per type)
SUMMARY:        Refactored from one-instance-per-type to multiple named instances per section type
STATUS:         CLOSED
TAGS:           sections, instances, phase-5
LINKS:          phase=COMPLETED.md-phase-5
---

## Description

Architectural refactor replacing the single-instance-per-type model with
a `SectionInstance[]` array:
- Each instance has `id`, `type`, `title`, `enabled`, `data`
- Multiple instances of the same type allowed (e.g. two Experience sections)
- Instance CRUD: add, remove, reorder, toggle, rename
- New CVs start with one enabled Profile instance
- Backend stores as JSONB in `cvs.sections`
- Frontend cvStore updated with instance-focused handlers

## Status

All Phase 5 tasks complete including T45-T46 tests.
