---
ID:             008
TYPE:           feature
NAME:           User-defined HTML templates
SUMMARY:        Upload custom HTML templates with zone placeholders for fully custom layouts
STATUS:         CLOSED
TAGS:           templates, user, phase-12
LINKS:          phase=COMPLETED.md-phase-12
---

## Description

Users can upload their own HTML templates:
- Upload via multipart (HTML file + optional zone JSON config)
- Templates use `{{zone_id}}` placeholders for section insertion
- CSS custom properties (`--accent`, `--body-font`, etc.) for customization
- CustomizePanel works with user templates via CSS variable substitution
- Auto-generate zones from HTML placeholders if not configured
- Full CRUD: list, upload, delete own templates
- `TEMPLATE_GUIDE.md` documents the format

## Status

All Phase 12 tasks complete. Backend and frontend tests were cancelled
due to test infrastructure issues.
