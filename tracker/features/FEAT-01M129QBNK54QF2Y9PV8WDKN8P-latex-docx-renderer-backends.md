---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN8P
TYPE: feature
STATUS: PROPOSED
SUMMARY: Extend IR-based renderer to output LaTeX and DOCX formats
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- future
- rendering
RELATIONS:
  related:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN8C
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:11:58.482296+00:00'
UPDATED_AT: '2026-08-01T16:11:58.482296+00:00'
---

# LaTeX/DOCX renderer backends

## Background

Extend IR-based renderer to output LaTeX and DOCX formats

The `RendererBackend` ABC in `renderer/backends/` already has the interface
ready. Add two new backends:
- `LaTeXBackend` → outputs `.tex` for academic/research CVs
- `DOCXBackend` → outputs `.docx` for corporate ATS systems

Each is a new subclass + `register_backend("latex", LaTeXBackend)`.

Proposed future enhancement (previously OPEN in the SCHEMA 2 tracker). Tags: future.
*Migrated from SCHEMA 2 entry 022-latex-docx-export.md (status OPEN) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from FEAT-01KYZ1HDMJRX33A5HEPJXGQ4FC during the schema-4 cutover. -->
