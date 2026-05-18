---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KYZ1HCMYDT2HS1JS7R4QAGHJ
TYPE: feature
STATUS: DONE
SUMMARY: 'Upload custom HTML templates with zone placeholders for fully custom layouts'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- templates
- user
- phase-12
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:11:57.470662+00:00'
UPDATED_AT: '2026-08-01T16:11:57.470662+00:00'
---

# User-defined HTML templates

## Background

Upload custom HTML templates with zone placeholders for fully custom layouts

Users can upload their own HTML templates:
- Upload via multipart (HTML file + optional zone JSON config)
- Templates use `{{zone_id}}` placeholders for section insertion
- CSS custom properties (`--accent`, `--body-font`, etc.) for customization
- CustomizePanel works with user templates via CSS variable substitution
- Auto-generate zones from HTML placeholders if not configured
- Full CRUD: list, upload, delete own templates
- `TEMPLATE_GUIDE.md` documents the format

*Migrated from SCHEMA 2 entry 008-user-defined-templates.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification

All Phase 12 tasks complete. Backend and frontend tests were cancelled
due to test infrastructure issues.

## Follow-up
