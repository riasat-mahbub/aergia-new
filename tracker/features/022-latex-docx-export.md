---
ID:             022
TYPE:           feature
NAME:           LaTeX/DOCX renderer backends
SUMMARY:        Extend IR-based renderer to output LaTeX and DOCX formats
STATUS:         OPEN
TAGS:           future, rendering
LINKS:          related-feature=012-ir-based-renderer
---

## Description

The `RendererBackend` ABC in `renderer/backends/` already has the interface
ready. Add two new backends:
- `LaTeXBackend` → outputs `.tex` for academic/research CVs
- `DOCXBackend` → outputs `.docx` for corporate ATS systems

Each is a new subclass + `register_backend("latex", LaTeXBackend)`.
