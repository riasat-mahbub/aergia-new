---
SCHEMA: 3
FORMAT: project-tracker
ID: EPIC-01KZCCC3MTXDGPY31H06NFYP1Q
TYPE: epic
STATUS: PLANNED
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS:
- renderer
- phase-7
- architecture
RELATIONS:
  related:
  - FEAT-01KZCCM17NP6QSKMGG71QV4PWF-html-first-pipeline
  - ADR-01KZCCM17NP6QSKMGG71QV4PWG-html-first-architecture
  - ADR-01KZCCM17NP6QSKMGG71QV4PWH-three-axis-style-model
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-06T20:31:26.362511+00:00'
UPDATED_AT: '2026-08-06T20:31:26.362511+00:00'
---

# HTML-first pipeline with three-axis style AST

## Background

Replace the legacy `SectionStyle` cascade (10 fields: font, color, weight, text_align, field_styles, show_title, layout, date_style, subsection_gap, row_gap) and the string-blob IR with a typed AST and an HTML-first render pipeline.

The current architecture claims to be renderer-agnostic. It isn't. The preview is HTML. The PDF is HTML rendered by Chromium. The CSS knowledge is HTML knowledge. The new architecture commits to what's actually true: HTML is the canonical rendering target.

**Branch:** `feat/ast-pipeline` (cut from master, merged via regular merge commit, not squash).

**Implementation reference:** AGENTS.md, PLAN.md, TEMPLATE_GUIDE.md, and the related FEAT/ADR entries below. No code yet; implementation references the docs.

## Goal

Build a new system from scratch on a separate branch that:
- Replaces the legacy `SectionStyle` cascade with three orthogonal axes (TextStyle, SubsectionStyle, LayoutHints).
- Replaces the string-blob IR with a typed AST (Pydantic models).
- Introduces an explicit Resolver stage that produces a fully resolved `RenderModel` before rendering.
- Replaces the string-concatenation renderer with a tree of small functions.
- Makes renderer capabilities a property of the renderer class (not a config dict).
- Treats the React tree as the editor surface, not a renderer.
- Uses design tokens (CSS variables) instead of hardcoded CSS values.

## Phase 0 — Foundation (docs only)

**Status:** DONE

| Task | Status |
|------|--------|
| Cut branch `feat/ast-pipeline` from master | ✅ |
| Update AGENTS.md with architecture promise, render model discipline, renderer capabilities, merge policy, pipeline diagram | ✅ |
| Update PLAN.md with Phase 7 (three-axis style model + HTML-first pipeline) | ✅ |
| Rewrite TEMPLATE_GUIDE.md for the new manifest pipeline | ✅ |
| Create FEAT-html-first-pipeline tracker entry | ✅ |
| Create ADR-html-first-architecture tracker entry | ✅ |
| Create ADR-three-axis-style-model tracker entry | ✅ |
| Create this EPIC tracker entry | ✅ |

## Phase 1 — Backend foundation (Pydantic AST + Resolver + Renderer)

**Status:** PLANNED

| Task | Status |
|------|--------|
| 1.0 Create `api/app/schema/models.py` with TextStyle, SubsectionStyle, LayoutHints, SectionPolicy, DocumentLayoutHints, DocumentStyles, Document, Section, Entry, FieldBlock, TextRun, SectionInstance, CVRow, Zone, ZoneStyle, LayoutConfig, LayoutDefaults, PolicyOverrides, DocumentLayout, Customizations, TemplateManifest | 🔲 |
| 1.1 Create `api/scripts/codegen_schema.py` (custom Pydantic-to-TS generator; CI checks no diff) | 🔲 |
| 1.2 Wire codegen into `dev.sh`, `Dockerfile`, `package.json` codegen script | 🔲 |
| 1.3 Add `SupportLevel` enum and `RendererSupport` class to `api/app/services/renderer/support.py` | 🔲 |
| 1.4 Add `SECTION_POLICIES` map and `resolve_policy()` to `api/app/services/renderer/policy.py` | 🔲 |
| 1.5 Add `build_ast()` and section builders to `api/app/services/renderer/build.py` and `api/app/services/renderer/builders/` | 🔲 |
| 1.6 Add `resolve()` and `RenderModel` to `api/app/services/renderer/resolve.py` (template defaults, policy resolution, CSS variable computation, design tokens) | 🔲 |
| 1.7 Add `HTMLDocumentRenderer` class to `api/app/services/renderer/html.py` (tree of small functions, `h()` escape helper) | 🔲 |
| 1.8 Add section renderers (one per type) to `api/app/services/renderer/section_renderers/` | 🔲 |
| 1.9 Add routes: `POST /render/ast`, `POST /render/html` | 🔲 |
| 1.10 Update `services/cv.py` and `services/pdf.py` to use the new schema and renderer | 🔲 |
| 1.11 Update `db/seed.py` with three minimal templates (Modern, Classic, Minimal) using `layout_defaults: { spacing: ... }` and `policy_overrides: {}` | 🔲 |
| 1.12 Add Phase 1 tests | 🔲 |

## Phase 2 — Frontend foundation (TS types + walker + customize panel)

**Status:** PLANNED

| Task | Status |
|------|--------|
| 2.0 Generate `web/src/generated/schema.ts` via codegen | 🔲 |
| 2.1 Create `web/src/lib/renderer/walk.ts` (TS AST walker for inline editor preview) | 🔲 |
| 2.2 Create React renderer components in `web/src/components/renderer/` (DocumentRenderer, SectionRenderer, EntryRenderer, TextRunRenderer) | 🔲 |
| 2.3 Update `CustomizePanel` to expose three disclosure groups (Layout, Block style, Field styles) | 🔲 |
| 2.4 Update `lib/sections/types.ts` to use the new generated types | 🔲 |
| 2.5 Update `lib/validators/sections.ts` (Zod) for the new types | 🔲 |
| 2.6 Update `sections/*/Editor.tsx` (8 files) to use the new structure | 🔲 |
| 2.7 Update `BuilderPage` to wire the new renderer | 🔲 |
| 2.8 Update `TemplateCreator` to use the new manifest schema | 🔲 |
| 2.9 Add Phase 2 tests | 🔲 |

## Phase 3 — Cutover and merge

**Status:** PLANNED

| Task | Status |
|------|--------|
| 3.0 Delete old code: `services/renderer/ir.py`, `services/renderer/types.py`, `services/renderer/backends/`, `services/renderer/section_renderers/` (replaced by `builders/`), `sections/*/Renderer.tsx` (8 files), `SectionPreviewPanel.tsx`, `SectionStyle` and `FieldStyle` interfaces | 🔲 |
| 3.1 Update `web/src/components/preview/UserTemplateRenderer.tsx` to use the new AST walker | 🔲 |
| 3.2 Merge `feat/ast-pipeline` into `master` via regular merge commit | 🔲 |
| 3.3 Verify the build is green: `pytest`, `npm run lint`, `npm run test`, `npm run build` | 🔲 |

## Investigation

See FEAT-html-first-pipeline, ADR-html-first-architecture, ADR-three-axis-style-model.

## Decision

HTML-first architecture. Three orthogonal axes for styling. Resolver produces RenderModel. Renderer is the source of truth for capabilities. SectionPolicy is document semantics. React tree is the editor surface. Design tokens replace hardcoded values. No migration code, no compatibility shims, no `X_LEGACY` shims. The old code dies on the merge.

## Implementation

The implementation order is the phase order above. Each phase is independently committable. The phases are designed so any single phase can be landed without breaking the build.

## Verification

After Phase 1: `pytest` passes; the new schema validates; the codegen produces no diff; the rendered HTML matches the current renderer for fixtures.

After Phase 2: `npm run lint` and `npm run test` pass; the customize panel renders three disclosure groups; the inline preview uses the new AST walker.

After Phase 3: `pytest`, `npm run lint`, `npm run test`, `npm run build` all pass on `master`. The old code is gone. The merge commit is the cutover.

## Follow-up

- LaTeX exporter (future): consumes AST, produces LaTeX.
- Real-time collaboration (future): the AST is the natural document representation for sharing.
