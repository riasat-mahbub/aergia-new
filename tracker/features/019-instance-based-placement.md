---
ID:             019
TYPE:           feature
NAME:           Instance-based zone placement (backend)
SUMMARY:        Update ir.py to map instance_id→zone_id instead of type→zone_id
STATUS:         CLOSED
TAGS:           zones, placement, backend, phase-6.1
LINKS:          phase=PLAN.md-phase-6.1
---

## Description

The frontend already supports instance-based placement (each instance can
be placed in a different zone). The backend `_group_instances_by_zone()` in
`ir.py` still maps `section_type → zone_id` as the primary lookup, only
falling back to instance ID. This should be swapped: primary lookup by
`instance_id`, fallback to `section_type` for old CVs.

## Why It Matters

Without this, two Profile instances cannot be placed in different zones
(e.g., one in sidebar, one in header) — the type-based fallback overrides
the instance ID mapping.
