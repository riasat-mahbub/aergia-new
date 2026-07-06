---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KZHR8NTSB4D8JZ4JX2D9THGE
TYPE: feature
STATUS: PLANNED
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: riasat
CONFIDENCE: Medium
TAGS:
- phase-7
- html-first
- three-axis
- renderer
- migrated
RELATIONS:
  part_of:
  - EPIC-01KZCCC3MTXDGPY31H06NFYP1Q
  related:
  - ADR-01KZHR8NXNVWPHJTQFE6E37V9G
  - ADR-01KZHR8P0PPWSZZPGYBT8HGGVT
  - TASK-01KZHR806TYQPTPEFG5JE8879C
AFFECTS: null
LINKS:
  plan: local://phase-7-closeout-phase-8-hardening-plan.md
  source: tracker/features/FEAT-01KZCCM17NP6QSKMGG71QV4PWF-html-first-pipeline.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-08T22:35:28.985516+00:00'
UPDATED_AT: '2026-08-08T22:35:28.985516+00:00'
---

# HTML-first pipeline (Phase 7) - migrated

## Background

Migrated from `tracker/features/FEAT-01KZCCM17NP6QSKMGG71QV4PWF-html-first-pipeline.md` (legacy lowercase frontmatter; original moved to `tracker-legacy/phase-7/`). The umbrella feature summary for the HTML-first pipeline with the three-axis style AST.

The current renderer is a string-concatenation function with no concept of what it's emitting. The `SectionStyle` cascade (10 fields: font, color, weight, text_align, field_styles, show_title, layout, date_style, subsection_gap, row_gap) conflates three different concerns: inline per-field appearance, block-level appearance, and page-flow intent. The customize panel flattens these into one "Style" disclosure and the user has to figure out which thing they meant.

The architecture document claims to be renderer-agnostic. It isn't. The preview is HTML. The PDF is HTML rendered by Chromium. The CSS knowledge is HTML knowledge. The "renderer-agnostic" framing is aspirational.

## Goals

- **HTML-first architecture.** The renderer is HTML. PDF is HTML via Chromium. The React tree is the editor surface, not a renderer.
- **Three orthogonal axes for styling:** TextStyle, SubsectionStyle, LayoutHints.
- **SectionPolicy is document semantics.** The HTML renderer implements it with HTML constructs; a future DOCX renderer implements it with DOCX constructs.
- **Resolver → RenderModel → Renderer.** The renderer receives a fully resolved document; no defaults remain.
- **Design tokens, not hardcoded values.** Templates declare `spacing: comfortable`; the renderer maps to CSS variables; the stylesheet defines the values.
- **Renderer capabilities are properties of the renderer.** `HTMLDocumentRenderer.support` is the source of truth.
- **Editor is schematic.** It visualizes structure (sections, fields, brackets), not the computed layout. Visual cues (e.g., page break markers) indicate structural intent without literal page boundaries.

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

## Pipeline (shipped signature)

1. `build_document(cv, manifest) -> Document` constructs the typed Pydantic AST.
2. `resolve(document, renderer, manifest, customizations) -> RenderModel` resolves defaults, policies, and design tokens; the renderer parameter's `support` gates which layout hints survive.
3. `HTMLDocumentRenderer.render(model) -> str` emits the HTML document.
4. Chromium renders the HTML to PDF.

## Implementation

This entry's implementation IS the EPIC. The closeout record is `local://phase-7-ast-pipeline-closeout.md`. Branch: `feat/ast-pipeline` (cut from `master`, merged via regular merge commit, not squash).

## Related

- `EPIC-01KZCCC3MTXDGPY31H06NFYP1Q-html-first-pipeline-with-three-axis-style-ast` — the umbrella epic
- `ADR-01KZHR8NXNVWPHJTQFE6E37V9G-html-first-architecture` — the architectural decision
- `ADR-01KZHR8P0PPWSZZPGYBT8HGGVT-three-axis-style-model` — the three-axis decision
- `TASK-01KZHR806TYQPTPEFG5JE8879C-phase-8-hardening-gate` — Phase 8 closeout verification
- `AGENTS.md`, `PLAN.md`, `local://phase-7-ast-pipeline-closeout.md`
