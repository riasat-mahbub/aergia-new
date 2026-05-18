---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KYZ1HDDXK2PHFQPFDW0XCC83
TYPE: feature
STATUS: DONE
SUMMARY: 'Update ir.py to map instance_id→zone_id instead of type→zone_id'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- zones
- placement
- backend
- phase-6.1
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:11:58.269272+00:00'
UPDATED_AT: '2026-08-01T16:11:58.269272+00:00'
---

# Instance-based zone placement (backend)

## Background

Update ir.py to map instance_id→zone_id instead of type→zone_id

The frontend already supports instance-based placement (each instance can
be placed in a different zone). The backend `_group_instances_by_zone()` in
`ir.py` still maps `section_type → zone_id` as the primary lookup, only
falling back to instance ID. This should be swapped: primary lookup by
`instance_id`, fallback to `section_type` for old CVs.

### Why It Matters

Without this, two Profile instances cannot be placed in different zones
(e.g., one in sidebar, one in header) — the type-based fallback overrides
the instance ID mapping.

*Migrated from SCHEMA 2 entry 019-instance-based-placement.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
