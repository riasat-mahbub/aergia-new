---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN82
TYPE: feature
STATUS: DONE
SUMMARY: Full CRUD for CVs with data isolation per user
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- cv
- crud
- phase-2
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:11:57.038048+00:00'
UPDATED_AT: '2026-08-01T16:11:57.038048+00:00'
---

# CV CRUD (list/create/get/update/delete/copy)

## Background

Full CRUD for CVs with data isolation per user

Complete CV management:
- List CVs for current user (sorted by update date)
- Create CV (with template selection)
- Get single CV
- Update CV (sections, customizations, template)
- Delete CV (soft delete via `is_active` flag)
- Copy/clone CV (independent deep copy)

*Migrated from SCHEMA 2 entry 002-cv-crud.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification

All Phase 2 tasks complete including T6-T12 tests.

## Follow-up

<!-- Migrated from FEAT-01KYZ1HC7DYBXKJ66538Z9P64K during the schema-4 cutover. -->
