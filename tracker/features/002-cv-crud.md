---
ID:             002
TYPE:           feature
NAME:           CV CRUD (list/create/get/update/delete/copy)
SUMMARY:        Full CRUD for CVs with data isolation per user
STATUS:         CLOSED
TAGS:           cv, crud, phase-2
LINKS:          phase=COMPLETED.md-phase-2
---

## Description

Complete CV management:
- List CVs for current user (sorted by update date)
- Create CV (with template selection)
- Get single CV
- Update CV (sections, customizations, template)
- Delete CV (soft delete via `is_active` flag)
- Copy/clone CV (independent deep copy)

## Status

All Phase 2 tasks complete including T6-T12 tests.
