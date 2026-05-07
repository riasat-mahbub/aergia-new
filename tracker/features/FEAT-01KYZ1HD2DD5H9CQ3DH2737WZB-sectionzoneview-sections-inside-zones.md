---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KYZ1HD2DD5H9CQ3DH2737WZB
TYPE: feature
STATUS: DONE
SUMMARY: 'Unified Content tab showing CV broken into rows/zones with sections rendered inside'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- zones
- ui
- phase-6
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:11:57.902049+00:00'
UPDATED_AT: '2026-08-01T16:11:57.902049+00:00'
---

# SectionZoneView (sections inside zones)

## Background

Unified Content tab showing CV broken into rows/zones with sections rendered inside

Replaced the flat SectionList with a zone-aware Content panel:
- CV rendered as rows → zones → sections
- Zone header: name, width%, gear (style panel), delete
- Inline ZoneStyleEditor: width, padding, bg, etc.
- Sections per zone: drag handle, title, type label, toggle, delete, expand editor
- Cross-zone DnD via single DndContext + DragOverlay
- Add Section per zone (new instance auto-assigned to that zone)
- Add Zone/Add Row modals with row reorder and horizontal resize handles
- Unassigned sections displayed in a draggable area

*Migrated from SCHEMA 2 entry 014-section-zone-merge.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification

Phase 6 complete except backend task 6.1 (instance-based placement in ir.py).

## Follow-up
