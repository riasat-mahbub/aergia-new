---
SCHEMA: 3
FORMAT: project-tracker
ID: DOC-01KYZ1XGE9FSXGDWY3T3SZHKDT
TYPE: doc
STATUS: PROPOSED
SUMMARY: 'TEMPLATE_GUIDE.md describes the old layout_template pipeline, not the manifest-driven system'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- docs
- template-guide
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:18:34.569894+00:00'
UPDATED_AT: '2026-08-01T16:18:34.569894+00:00'
---

# TEMPLATE_GUIDE.md needs rewrite for manifest format

## Background

TEMPLATE_GUIDE.md describes the old layout_template pipeline, not the manifest-driven system

The current `TEMPLATE_GUIDE.md` was written for the old user template
system (HTML-only templates with `{{zone_id}}` placeholders). The
manifest-driven pipeline has replaced this, but the guide hasn't been
updated. It references deprecated concepts:
- `layout_template` instead of manifest
- Zone configuration at upload time (now handled by the visual wizard)
- Old customization panel behavior

### What It Should Cover

- Manifest JSON schema reference
- Visual wizard flow (Step 1-4)
- Generated HTML/CSS from manifest
- Asset loading

*Migrated from SCHEMA 2 entry 006-template-guide-rewrite.md (status OPEN) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
