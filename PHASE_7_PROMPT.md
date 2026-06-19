# Phase 7 Intent

You are implementing a new render pipeline for the Aergia CV Builder. The architecture is already committed to in writing. Read the docs first, then execute.

## The one-paragraph summary

The current renderer is a string-concatenation function. The legacy `SectionStyle` (10 fields) conflates three different concerns — inline per-field appearance, block-level appearance, and page-flow intent. The customize panel flattens these into one disclosure. The "renderer-agnostic" framing is aspirational; the reality is HTML-first. The new system replaces the legacy with a typed AST, three orthogonal axes (`TextStyle`, `SubsectionStyle`, `LayoutHints`), an explicit Resolver stage, and a renderer that declares its own capabilities. The React tree is the editor surface, not a renderer. The merge is a regular merge commit, not a squash.

## The intent of the change

The current architecture has four problems that cumulate:

1. **String-concatenation renderer.** The IR is a manually-built string blob. Hard to test, hard to extend, easy to break in subtle ways.
2. **Conflated styling.** `SectionStyle` mixes inline per-field, block-level, and page-flow concerns. The customize panel can't tell them apart; the user can't tell them apart.
3. **Render drift.** The Python HTML renderer and the React renderer (the former under `web/src/components/sections/*Renderer.tsx`) drift. A snapshot test catches it but doesn't prevent it.
4. **HTML knowledge scattered.** CSS values are hardcoded. The renderer knows `24px`. The customize panel hides this fact, but the underlying rigidity is real.

The new architecture solves all four:

1. **Pydantic schema as AST.** The Pydantic models in `api/app/schema/models.py` are both the wire shape and the runtime AST. They're the source of truth. TypeScript types are generated from them via codegen.
2. **Three orthogonal axes.** `TextStyle` (inline per-field), `SubsectionStyle` (block-level), `LayoutHints` (page flow + structural). Each lives on its own data structure. The customize panel exposes three disclosure groups.
3. **Resolver → RenderModel → Renderer.** The renderer receives a fully resolved document. No defaults, no conditional logic, no "what does the user want" decisions. The renderer is almost stupid.
4. **Design tokens.** Templates declare `spacing: comfortable`. The renderer maps to CSS variables. The stylesheet defines the values. Three layers, each independent.

## The how

The implementation follows a `AST → Resolver → Renderer` pipeline. The renderer is HTML. PDF is HTML rendered by Chromium. React tree is the editor surface.

**The schema is the AST.** Pydantic models in `api/app/schema/models.py` define every typed shape — the three style axes, the AST nodes (`Document`, `Section`, `Entry`, `FieldBlock`, `TextRun`), the wire carriers (`SectionInstance`, `CVRow`, `TemplateManifest`, `Customizations`). The codegen script produces TypeScript types in `web/src/generated/schema.ts`. CI checks that running codegen produces no diff.

**The Resolver is the new stage.** Takes the AST + template + renderer's capabilities, produces a `RenderModel`. Applies template defaults, resolves policies, computes CSS variables from design tokens, resolves font choices. By the time the renderer sees the document, every decision has been made.

**The renderer is the source of truth for its capabilities.** `HTMLDocumentRenderer.support` returns a `RendererSupport` with per-field `SupportLevel` (FULL, BEST_EFFORT, NONE). The customize panel reads the renderer's support. The export endpoint reads the renderer's support. Capabilities are not a config dict; they're a property of the renderer.

**SectionPolicy is document semantics.** The HTML renderer implements it with HTML constructs; a future DOCX renderer implements it with DOCX constructs. The policy stays semantic.

**The editor is schematic.** The React tree visualizes the document structure (sections, fields, brackets). It does not promise to show the exact spacing, page breaks, or font fallbacks the PDF will produce. Visual cues (e.g., "page break" markers) indicate structural intent without literal page boundaries.

**The merge is a regular merge commit.** The branch's commit history is preserved on master. The merge is the cutover — the old code is gone in one step.

## The phase plan

The work is broken into three phases. Each phase is independently committable. The phases are designed so any single phase can be landed without breaking the build.

### Phase 1 — Backend foundation

The Pydantic schema, the codegen, the Resolver, the renderer, the routes, the services, the seed templates, the tests.

**Goal:** The backend can build the AST, resolve it, render it to HTML, and export to PDF. The customize panel and the frontend editor are not yet changed.

**Tasks:**

1. Create `api/app/schema/models.py` with the full Pydantic schema (text styles, subsection styles, layout hints, section policy, document styles, AST nodes, wire carriers).
2. Create `api/scripts/codegen_schema.py` — a custom Pydantic-to-TypeScript generator. The existing `datamodel-code-generator` and `pydantic-to-typescript` tools have dependency issues; write a small custom script that reads `model_json_schema()` and emits TypeScript interfaces. The script must produce stable output (double quotes, TS 5.6 target).
3. Wire codegen into the build:
   - `dev.sh` runs codegen after `pip install`, before `alembic upgrade head`.
   - `Dockerfile` adds a codegen stage that runs before the frontend build.
   - `package.json` adds `codegen` and `codegen:check` scripts.
   - `pyproject.toml` adds the codegen dependency to a `[codegen]` optional extras group.
4. Generate `web/src/generated/schema.ts` and commit it. CI checks no diff.
5. Add `api/app/services/renderer/support.py` with `SupportLevel` enum and `RendererSupport` dataclass.
6. Add `api/app/services/renderer/policy.py` with `SECTION_POLICIES` map and `resolve_policy()` helper.
7. Add `api/app/services/renderer/build.py` with `build_ast()` and section builders (one per type) under `api/app/services/renderer/builders/`.
8. Add `api/app/services/renderer/resolve.py` with `resolve()` and `RenderModel`. The Resolver applies template defaults, resolves policies, computes CSS variables from design tokens.
9. Add `api/app/services/renderer/html.py` with `HTMLDocumentRenderer` class. Tree of small functions (one per AST node type). A single `h()` escape helper. The renderer is the source of truth for its capabilities.
10. Add `api/app/services/renderer/section_renderers/` with one file per type (profile, experience, education, skills, projects, languages, certifications, research).
11. Add routes in `api/app/routes/render.py`:
    - `POST /render/ast` — returns the AST as JSON.
    - `POST /render/html` — returns rendered HTML.
    - `POST /render/{target}` — returns the rendered output for the target format (HTML, PDF, future DOCX).
12. Update `api/app/services/cv.py` and `api/app/services/pdf.py` to use the new schema and renderer.
13. Update `api/app/db/seed.py` with three minimal templates (Modern, Classic, Minimal) using `layout_defaults: { spacing: ... }` and `policy_overrides: {}`.
14. Add Phase 1 tests.

### Phase 2 — Frontend foundation

The TypeScript types, the AST walker, the React renderer components, the CustomizePanel rewrite, the section editors, the Builder page, the template creator, the tests.

**Goal:** The frontend uses the new schema. The customize panel exposes three disclosure groups. The inline preview uses the new AST walker.

**Tasks:**

1. `web/src/lib/sections/types.ts` re-exports the generated types. Hand-written wrappers only where the generated types are too verbose.
2. `web/src/lib/validators/sections.ts` updated Zod schemas for the new types.
3. `web/src/lib/renderer/walk.ts` — a TS AST walker for the inline editor preview. Mirrors the Python serializer's tree shape.
4. `web/src/components/renderer/` — tree-walking React components (`DocumentRenderer`, `SectionRenderer`, `EntryRenderer`, `TextRunRenderer`).
5. `web/src/components/customization/CustomizePanel.tsx` — rewrite to expose three disclosure groups (Layout, Block style, Field styles). Reads the renderer's support for control visibility.
6. `web/src/components/sections/SectionRegistry.tsx` — editor registry only (no `*Renderer.tsx` files).
7. `web/src/components/sections/{profile,experience,education,skills,projects,languages,certifications,research}/Editor.tsx` — updated to use the new structure.
8. `web/src/components/customization/LayoutHintsEditor.tsx` — new component for the Layout disclosure group.
9. `web/src/components/preview/UserTemplateRenderer.tsx` — uses the new AST walker for the inline preview.
10. `web/src/pages/BuilderPage.tsx` — wires the new renderer.
11. `web/src/components/template-creator/` — uses the new manifest schema.
12. Add Phase 2 tests.

### Phase 3 — Cutover and merge

Delete the old code, merge into master.

**Goal:** The old code is gone. The new code is the only code. The merge commit is the cutover.

**Tasks:**

1. Delete the old code:
   - `api/app/services/renderer/ir.py`
   - `api/app/services/renderer/types.py`
   - `api/app/services/renderer/backends/`
   - `api/app/services/renderer/section_renderers/` (replaced by `builders/`)
   - `web/src/components/sections/*/Renderer.tsx` (8 files)
   - `web/src/components/sections/SectionPreviewPanel.tsx`
   - `SectionStyle` and `FieldStyle` interfaces in `web/src/lib/sections/types.ts`
   - `web/src/lib/sections/fieldStyles.ts` (or rewrite as a pure registry)
2. Merge `feat/ast-pipeline` into `master` via a regular merge commit.
3. Verify the build: `pytest`, `npm run lint`, `npm run test`, `npm run build` all pass.

## The rules

1. **HTML-first.** The renderer is HTML. PDF is HTML rendered by Chromium. The React tree is the editor surface, not a renderer.
2. **Three orthogonal axes.** `TextStyle` (per-field inline), `SubsectionStyle` (block-level), `LayoutHints` (page flow + structural). No fourth axis.
3. **SectionPolicy is document semantics.** The HTML renderer implements it with HTML constructs; a future DOCX renderer implements it with DOCX constructs. The policy stays semantic.
4. **Capabilities are properties of the renderer.** `HTMLDocumentRenderer.support` is the source of truth. The customize panel and export endpoint read the renderer.
5. **Editor is schematic.** It visualizes structure, not the computed layout. Visual cues (e.g., "page break" markers) indicate structural intent.

## The branch

`feat/ast-pipeline` — cut from master. Implementation happens on this branch. The merge is a regular merge commit (not squash). The branch's commit history is preserved on master.

## What to read

The full architecture and rationale are in:

- **`AGENTS.md`** — architecture promise, render model discipline, renderer capabilities, merge policy, pipeline diagram.
- **`PLAN.md`** — Phase 7 with the full task list.
- **`TEMPLATE_GUIDE.md`** — the new manifest pipeline.
- **Tracker entries:**
  - `EPIC-01KZCCC3MTXDGPY31H06NFYP1Q-html-first-pipeline-with-three-axis-style-ast` — the umbrella with the full phase plan.
  - `FEAT-01KZCCM17NP6QSKMGG71QV4PWF-html-first-pipeline` — feature-level summary.
  - `ADR-01KZCCM17NP6QSKMGG71QV4PWG-html-first-architecture` — the architectural decision.
  - `ADR-01KZCCM17NP6QSKMGG71QV4PWH-three-axis-style-model` — the three-axis decision.

Read these first. The prompt is the summary; the docs are the implementation reference.

## What to not do

1. **Don't reimplement Python logic in TypeScript.** The codegen bridge is for types only. Runtime logic stays on the backend. If you find yourself writing a Zod validator that mirrors a Pydantic validator, that's a design smell — move the logic to the backend.
2. **Don't add backward compatibility shims.** The old code dies on the merge. No `X_LEGACY` shims, no `_resolve_legacy_*` functions, no "preserve old behavior" tests. The branch lives; the merge is the cutover.
3. **Don't squash the merge.** The branch's commit history is preserved on master. The merge is a regular merge commit.

## What to do

1. **Read the docs.** AGENTS.md, PLAN.md, TEMPLATE_GUIDE.md. The EPIC + FEAT + ADRs.
2. **Commit incrementally.** Each commit is independently buildable. The branch's history tells the story of the new system being built.
3. **Follow the phase order.** Phase 1 (backend) → Phase 2 (frontend) → Phase 3 (cutover). Each phase is independently committable.

## The pipeline (one more time)

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

The React tree is the editor surface. It mirrors the AST but doesn't render HTML. The Python HTML renderer is the document renderer. Both consume the same data; the rendering is different.

## Start

Begin with Phase 1.1: create `api/app/schema/models.py` with the schema. The detailed model definitions are in the FEAT entry's "Schema additions" section. Then the codegen script. Then the Resolver. Then the renderer. The phase order is the order in the EPIC.

The docs are the implementation reference. The prompt is the summary. The implementation is the code that follows.
