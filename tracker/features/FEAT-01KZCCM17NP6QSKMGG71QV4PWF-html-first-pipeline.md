---
id: FEAT-01KZCCM17NP6QSKMGG71QV4PWF-html-first-pipeline
title: HTML-first pipeline with three-axis style AST
status: PLANNED
created: 2026-08-06
updated: 2026-08-06
---

# HTML-first pipeline with three-axis style AST

## Summary

This is a feature-level entry for the new render pipeline. The full phase plan lives in the EPIC. See **EPIC-01KZCCC3MTXDGPY31H06NFYP1Q** for phases, tasks, and the merge plan.

## Background

The current renderer is a string-concatenation function with no concept of what it's emitting. The `SectionStyle` cascade (10 fields: font, color, weight, text_align, field_styles, show_title, layout, date_style, subsection_gap, row_gap) conflates three different concerns: inline per-field appearance, block-level appearance, and page-flow intent. The customize panel flattens these into one "Style" disclosure and the user has to figure out which thing they meant.

The architecture document claims to be renderer-agnostic. It isn't. The preview is HTML. The PDF is HTML rendered by Chromium. The CSS knowledge is HTML knowledge. The "renderer-agnostic" framing is aspirational.

## Goals

- **HTML-first architecture.** The renderer is HTML. PDF is HTML via Chromium. The React tree is the editor surface, not a renderer.
- **Three orthogonal axes for styling:** TextStyle, SubsectionStyle, LayoutHints.
- **SectionPolicy is document semantics.** The HTML renderer implements it with HTML constructs; a future DOCX renderer implements it with DOCX constructs.
- **Resolver → RenderModel → Renderer.** The renderer receives a fully resolved document; no defaults remain.
- **Design tokens, not hardcoded values.** Templates declare `spacing: comfortable`; the renderer maps to CSS variables; the stylesheet defines the values.
- **Renderer capabilities are properties of the renderer.** `HTMLDocumentRenderer.support` is the source of truth.
- **Editor is schematic.** It visualizes structure (sections, fields, brackets), not the computed layout. Visual cues (e.g., "page break" markers) indicate structural intent without literal page boundaries.

## Architecture

```
AST (Pydantic schemas)
  ↓
Resolver (apply template defaults, resolve policies, compute CSS variables)
  ↓
RenderModel (fully resolved; no defaults remain)
  ↓
HTMLDocumentRenderer (almost stupid; emits HTML)
  ↓
HTML5 + CSS
  ↓
Chromium
  ↓
PDF
```

## Pipeline

1. `build_ast(cv_data, customizations, template)` → `Document` (Pydantic AST).
2. `resolve(document, template, renderer.support)` → `RenderModel` (fully resolved).
3. `HTMLDocumentRenderer.render(model)` → HTML5 string.
4. `Chromium` → PDF bytes.

## Implementation

This entry's implementation IS the EPIC. See EPIC-01KZCCC3MTXDGPY31H06NFYP1Q for phases, tasks, and the merge plan.

Branch: `feat/ast-pipeline` (cut from master, merged via regular merge commit, not squash).

## Related

- EPIC-01KZCCC3MTXDGPY31H06NFYP1Q-html-first-pipeline-with-three-axis-style-ast
- ADR-01LZ000000000000000000000-html-first-architecture
- ADR-01LZ000000000000000000000-three-axis-style-model
- AGENTS.md, PLAN.md, TEMPLATE_GUIDE.md
