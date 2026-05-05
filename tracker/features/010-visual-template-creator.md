---
ID:             010
TYPE:           feature
NAME:           Visual template creator wizard
SUMMARY:        4-step guided wizard for creating templates with zone layout, styles, assets, and review
STATUS:         CLOSED
TAGS:           template-creator, wizard, phase-5
LINKS:          phase=PLAN.md-phase-5
---

## Description

Guided wizard replacing the old two-tab template creator:
- **Step 1 — Layout**: ZoneLayoutBar with rows, zones, drag-resize, placement
- **Step 2 — Global Styles**: StyleEditor built dynamically from `globalStyleSchema`
- **Step 3 — Assets**: Drag-drop for fonts/images
- **Step 4 — Review**: Read-only HTML preview
- Save generates multipart POST to `/api/v1/templates` with manifest + HTML + assets
- System templates are read-only (grouped as `is_system=true`)
- `BaseTemplateCard` thumbnails generated from manifest

## Status

Phase 5 complete. Task 5.7 (TEMPLATE_GUIDE.md rewrite) and 5.8 (E2E test) pending.
