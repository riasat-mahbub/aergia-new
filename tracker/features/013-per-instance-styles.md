---
ID:             013
TYPE:           feature
NAME:           Per-instance style overrides
SUMMARY:        Per-section-instance font, color, and weight overrides in the Customize panel
STATUS:         CLOSED
TAGS:           styles, customization, phase-10.5
LINKS:          phase=COMPLETED.md-phase-10.5
---

## Description

Individual section instances can override global styles:
- `SectionStyle` type added: `font`, `color`, `weight`
- Inline styles applied to wrapper div and heading in `SectionPreviewPanel`
- Backend `renderer.py` applies per-instance styles in `render_instance_panel`
- Template change strips all per-instance styles
- Accordion UI per section in CustomizePanel

## Status

Phase 10.5 complete. Tests T11.2-T11.5 still pending.
