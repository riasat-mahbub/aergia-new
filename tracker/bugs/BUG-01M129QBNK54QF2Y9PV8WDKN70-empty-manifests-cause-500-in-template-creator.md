---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M129QBNK54QF2Y9PV8WDKN70
TYPE: bug
STATUS: DONE
SUMMARY: Template creator crashed with 500 error when manifest had empty zones or
  missing fields
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- template-creator
- manifest
- '500'
- validation
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:09:35.504187+00:00'
UPDATED_AT: '2026-08-01T16:09:35.504187+00:00'
---

# Empty manifests cause 500 in template creator

## Background

Template creator crashed with 500 error when manifest had empty zones or missing fields

The template creator endpoint crashed with a 500 Internal Server Error
when the manifest JSON had empty zones arrays or missing required fields.
There was no validation step before the manifest was processed.

*Migrated from SCHEMA 2 entry 004-empty-manifest-500.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation

Added explicit validation for `layout_config`, zones, and section types
with descriptive error messages instead of letting the server crash with
a 500.

### Commit
`a84708a` — Fix 500 errors from empty manifests in template creator

## Verification


## Follow-up

<!-- Migrated from BUG-01KYZ1D20GRTWMQ5HE27MJET0H during the schema-4 cutover. -->
