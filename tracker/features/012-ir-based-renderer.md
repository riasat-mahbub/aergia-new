---
ID:             012
TYPE:           feature
NAME:           IR-based renderer with pluggable backends
SUMMARY:        Pure-function intermediate representation pipeline separating logic from output format
STATUS:         CLOSED
TAGS:           renderer, ir, phase-3
LINKS:          phase=PLAN.md-phase-3
---

## Description

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

## Status

Phase 3 complete.
