---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KYZ1HD041TCC8X6GW22KYFSA
TYPE: feature
STATUS: DONE
SUMMARY: 'Per-section-instance font, color, and weight overrides in the Customize panel'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- styles
- customization
- phase-10.5
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:11:57.828933+00:00'
UPDATED_AT: '2026-08-01T16:11:57.828933+00:00'
---

# Per-instance style overrides

## Background

Per-section-instance font, color, and weight overrides in the Customize panel

Individual section instances can override global styles:
- `SectionStyle` type added: `font`, `color`, `weight`
- Inline styles applied to wrapper div and heading in `SectionPreviewPanel`
- Backend `renderer.py` applies per-instance styles in `render_instance_panel`
- Template change strips all per-instance styles
- Accordion UI per section in CustomizePanel

*Migrated from SCHEMA 2 entry 013-per-instance-styles.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification

Phase 10.5 complete. Tests T11.2-T11.5 still pending.

## Follow-up
