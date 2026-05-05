---
ID:             014
TYPE:           feature
NAME:           SectionZoneView (sections inside zones)
SUMMARY:        Unified Content tab showing CV broken into rows/zones with sections rendered inside
STATUS:         CLOSED
TAGS:           zones, ui, phase-6
LINKS:          phase=PLAN.md-phase-6
---

## Description

Replaced the flat SectionList with a zone-aware Content panel:
- CV rendered as rows → zones → sections
- Zone header: name, width%, gear (style panel), delete
- Inline ZoneStyleEditor: width, padding, bg, etc.
- Sections per zone: drag handle, title, type label, toggle, delete, expand editor
- Cross-zone DnD via single DndContext + DragOverlay
- Add Section per zone (new instance auto-assigned to that zone)
- Add Zone/Add Row modals with row reorder and horizontal resize handles
- Unassigned sections displayed in a draggable area

## Status

Phase 6 complete except backend task 6.1 (instance-based placement in ir.py).
