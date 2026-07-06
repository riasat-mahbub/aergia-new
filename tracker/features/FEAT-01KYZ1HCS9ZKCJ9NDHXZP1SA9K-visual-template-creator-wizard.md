---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KYZ1HCS9ZKCJ9NDHXZP1SA9K
TYPE: feature
STATUS: DONE
---

# Visual template creator wizard

## Background

4-step guided wizard for creating templates with zone layout, styles, assets, and review

Guided wizard replacing the old two-tab template creator:
- **Step 1 — Layout**: ZoneLayoutBar with rows, zones, drag-resize, placement
- **Step 2 — Global Styles**: StyleEditor built dynamically from `globalStyleSchema`
- **Step 3 — Assets**: Drag-drop for fonts/images
- **Step 4 — Review**: Read-only HTML preview
- Save generates multipart POST to `/api/v1/templates` with manifest + HTML + assets
- System templates are read-only (grouped as `is_system=true`)
- `BaseTemplateCard` thumbnails generated from manifest

*Migrated from SCHEMA 2 entry 010-visual-template-creator.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification

Phase 5 complete. Task 5.7 (TEMPLATE_GUIDE.md rewrite) and 5.8 (E2E test) pending.

## Follow-up
Closed 2026-08-08. Superseded by `FEAT-01KZPHASE6STEP1-phase-6-content-only-authoring`. The template-authoring surface is deleted entirely; templates are now a closed, typed vocabulary owned by Aergia. Users pick from the three seed templates (modern, classic, minimal) and never author one. See `local://phase-6-content-only-authoring-plan.md`.
