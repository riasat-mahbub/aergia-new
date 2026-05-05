---
ID:             004
TYPE:           bug
NAME:           Empty manifests cause 500 in template creator
SUMMARY:        Template creator crashed with 500 error when manifest had empty zones or missing fields
STATUS:         CLOSED
TAGS:           template-creator, manifest, 500, validation
LINKS:          fix-commit=a84708a
---

## Description

The template creator endpoint crashed with a 500 Internal Server Error
when the manifest JSON had empty zones arrays or missing required fields.
There was no validation step before the manifest was processed.

## Resolution

Added explicit validation for `layout_config`, zones, and section types
with descriptive error messages instead of letting the server crash with
a 500.

### Commit
`a84708a` — Fix 500 errors from empty manifests in template creator
