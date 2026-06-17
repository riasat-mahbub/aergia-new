---
id: ADR-01LZ000000000000000000000-html-first-architecture
title: HTML-first architecture
status: DONE
created: 2026-08-06
updated: 2026-08-06
---

# HTML-first architecture

## Context

The current architecture claims to be renderer-agnostic. It isn't. The preview is HTML. The PDF is HTML rendered by Chromium. The CSS knowledge is HTML knowledge. The React tree is the editor surface. The "renderer-agnostic" framing is aspirational.

The codebase has parallel renderers (Python HTML and React JSX) that drift. The customize panel flattens three concerns (inline per-field, block-level, page-flow) into one Disclosure. The `SectionStyle` cascade (10 fields) conflates these. The result is a system that's hard to extend, hard to debug, and hard to test.

## Decision

The new system is HTML-first:

1. **The canonical rendering target is HTML + CSS.** The preview iframe, the PDF export, and any future HTML-based output all go through the same Python HTML renderer.
2. **PDF export is HTML rendered by Chromium.** Not a separate engine.
3. **The React tree is the editor surface, not a renderer.** It does not produce HTML for the preview or PDF. The preview and PDF are produced by the Python HTML renderer.
4. **The renderer is named `HTMLDocumentRenderer`.** The base class is `DocumentRenderer`. Future renderers extend the base.
5. **Capabilities are properties of the renderer.** `HTMLDocumentRenderer.support` is the source of truth. The customize panel and export endpoint read the renderer.
6. **SectionPolicy is document semantics, not HTML-oriented.** The HTML renderer implements it; a future DOCX renderer would implement it differently.

## Consequences

- **One renderer, not two.** The React tree is the editor; the Python HTML renderer is the document. No drift.
- **Templates express taste; renderers express behavior.** Seed templates declare `layout_defaults: { spacing: comfortable }`; the renderer maps to CSS variables; the stylesheet defines the values.
- **Logic stays on the backend.** Pydantic models are data shapes; validation lives in the service layer. The codegen bridge is for types only.
- **The editor is schematic.** It visualizes structure (sections, fields, brackets), not the computed layout. Visual cues (e.g., page break markers) indicate structural intent without literal page boundaries.

## Pipeline

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

## Alternatives considered

- **Renderer-agnostic architecture.** Rejected because the application is HTML-centric; the abstraction doesn't pay for itself.
- **Client-side React rendering of the preview.** Rejected because the PDF needs to be HTML-rendered by Chromium, and the client-side render would drift from the server-side render.
- **String-concatenation renderer with no separation.** Rejected because the renderer is hard to test and hard to extend.

## Related

- AGENTS.md, PLAN.md, TEMPLATE_GUIDE.md
- FEAT-html-first-pipeline
