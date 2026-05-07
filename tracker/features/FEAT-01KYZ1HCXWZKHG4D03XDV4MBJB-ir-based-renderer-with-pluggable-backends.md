---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KYZ1HCXWZKHG4D03XDV4MBJB
TYPE: feature
STATUS: DONE
SUMMARY: 'Pure-function intermediate representation pipeline separating logic from output format'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- renderer
- ir
- phase-3
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:11:57.756938+00:00'
UPDATED_AT: '2026-08-01T16:11:57.756938+00:00'
---

# IR-based renderer with pluggable backends

## Background

Pure-function intermediate representation pipeline separating logic from output format

New renderer package at `api/app/services/renderer/`:
- **Intermediate Representation (IR)**: `DocumentIR`, `RowIR`, `ZoneIR`, `SectionPanelIR`
- `build_ir()` builds IR from manifest + CV data + customizations (pure, no I/O)
- Pluggable backends via `RendererBackend` ABC:
  - `HTMLBackend` → emits complete HTML5
  - `PDFBackend` → async Playwright rendering
  - Extensible: add LaTeX/DOCX via new subclass + `register_backend()`
- `ir.py` handles zone layout, width normalization, CSS var resolution
- `section_renderers/` package with one file per section type
- Legacy renderer deleted

*Migrated from SCHEMA 2 entry 012-ir-based-renderer.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification

Phase 3 complete.

## Follow-up
