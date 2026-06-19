# Phase 7 Implementation Prompt

You are implementing the new render pipeline for the Aergia CV Builder. The architecture is fully designed and committed to in the docs. This prompt is how you execute.

## The three docs that are the implementation reference

1. **`AGENTS.md`** — the architecture promise, render model discipline, renderer capabilities, merge policy, pipeline diagram. Read this first.
2. **`PLAN.md`** — Phase 7 (three-axis style model + HTML-first pipeline). Read this for the phase structure.
3. **`TEMPLATE_GUIDE.md`** — the new manifest pipeline. Read this for the manifest schema and design tokens.

The tracker entries (EPIC + FEAT + 2 ADRs) link these together and document the full phase plan with task-level granularity.

## The architecture in one sentence

The renderer is HTML. PDF is HTML rendered by Chromium. The React tree is the editor surface, not a renderer. The schema is Pydantic. The pipeline is `AST → Resolver → RenderModel → Renderer`.

## The four layers

**1. Pydantic schema (the source of truth).**
- `api/app/schema/models.py` — Pydantic models that are both the wire shape and the runtime AST.
- Place at `api/app/schema/models.py`. The file content is fully specified in the FEAT entry.
- Models: `TextStyle`, `SubsectionStyle`, `LayoutHints`, `SectionPolicy`, `DocumentLayoutHints`, `DocumentStyles`, `Document`, `Section`, `Entry`, `FieldBlock`, `TextRun`, `SectionInstance`, `CVRow`, `Zone`, `ZoneStyle`, `LayoutConfig`, `LayoutDefaults`, `PolicyOverrides`, `DocumentLayout`, `Customizations`, `TemplateManifest`.

**2. AST JSON output (codegen).**
- Generate `web/src/generated/schema.ts` from the Pydantic schema.
- Use a custom Python script at `api/scripts/codegen_schema.py` (the existing `datamodel-code-generator` and `pydantic-to-typescript` tools have dependency issues — write a small custom generator that reads `model_json_schema()` and walks the JSON Schema to emit TypeScript interfaces).
- The custom generator must use double quotes, target TS 5.6, produce stable output.
- CI checks: `python -m scripts.codegen_schema` produces no diff vs the committed file.

**3. Resolver + RenderModel.**
- `api/app/services/renderer/resolve.py` — the new stage.
- `resolve(document, template, renderer.support)` → `RenderModel` (fully resolved; no defaults remain).
- The Resolver applies template defaults, resolves policies, computes CSS variables from design tokens, resolves font choices.
- Design tokens: `spacing: comfortable` → CSS variable → stylesheet value. Three layers, each independent.

**4. Renderer.**
- `api/app/services/renderer/html.py` — `HTMLDocumentRenderer` class.
- Tree of small functions (one per AST node type). Each function returns an HTML string. Composition is string concatenation.
- A single `h()` escape helper is the only escape call.
- The renderer is the source of truth for its capabilities.
- `HTMLDocumentRenderer.support` returns a `RendererSupport` with per-field `SupportLevel` (FULL, BEST_EFFORT, NONE).

## The five rules

1. **HTML-first.** The renderer is HTML. PDF is HTML rendered by Chromium. The React tree is the editor surface, not a renderer.
2. **Three orthogonal axes.** TextStyle (per-field inline), SubsectionStyle (block-level), LayoutHints (page flow + structural). No fourth axis.
3. **SectionPolicy is document semantics.** The HTML renderer implements it with HTML constructs; a future DOCX renderer implements it with DOCX constructs. The policy stays semantic.
4. **Capabilities are properties of the renderer.** `HTMLDocumentRenderer.support` is the source of truth. The customize panel and export endpoint read the renderer.
5. **Editor is schematic.** It visualizes structure, not the computed layout. Visual cues (e.g., "page break" markers) indicate structural intent.

## The branch

`feat/ast-pipeline` — cut from master, never merged into master. Implementation happens on this branch. The merge is a regular merge commit (not squash). The branch's commit history is preserved on master.

## The order

The implementation order is the phase order in the EPIC:

- **Phase 1** (backend): codegen + schemas + Resolver + Renderer + routes + services + seed templates + tests.
- **Phase 2** (frontend): TS types + walker + React renderer components + CustomizePanel rewrite + section editors + Builder page + template creator + tests.
- **Phase 3** (cutover): delete old code, merge into master.

Each phase is independently committable. The phases are designed so any single phase can be landed without breaking the build.

## The merge

The merge is a regular merge commit. The branch's commit history is preserved on master. The merge is the cutover — the old code is gone in one step.

## What the implementation looks like

### Phase 1 — backend foundation

```
api/app/schema/
└── models.py                                       # NEW: Pydantic source of truth

api/scripts/
└── codegen_schema.py                                # NEW: custom Pydantic → TS generator

api/app/services/renderer/
├── support.py                                       # NEW: SupportLevel enum, RendererSupport class
├── policy.py                                        # NEW: SECTION_POLICIES, resolve_policy()
├── build.py                                         # NEW: build_ast(), section builders
├── resolve.py                                       # NEW: Resolver, RenderModel
├── html.py                                          # NEW: HTMLDocumentRenderer class
└── section_renderers/                               # NEW: one per type (profile, experience, etc.)

api/app/services/
├── cv.py                                            # USE the new schema
└── pdf.py                                           # USE the new renderer

api/app/routes/
├── render.py                                        # NEW: POST /render/ast, POST /render/html
└── cvs.py                                           # USE the new schema

api/app/db/seed.py                                   # USE the new minimal templates

web/src/generated/
└── schema.ts                                        # NEW: generated TS types
```

### Phase 2 — frontend foundation

```
web/src/lib/renderer/
└── walk.ts                                          # NEW: TS AST walker

web/src/components/renderer/
├── DocumentRenderer.tsx                             # NEW
├── SectionRenderer.tsx                              # NEW
├── EntryRenderer.tsx                                # NEW
└── TextRunRenderer.tsx                              # NEW

web/src/components/customization/
└── CustomizePanel.tsx                               # REWRITE: three disclosure groups

web/src/components/sections/
├── SectionRegistry.tsx                              # REWRITE: editor registry only
├── {profile,experience,education,skills,projects,languages,certifications,research}/
│   └── Editor.tsx                                   # REWRITE: use new structure
└── ...

web/src/components/preview/
└── UserTemplateRenderer.tsx                         # USE the new AST walker

web/src/pages/
└── BuilderPage.tsx                                  # WIRE the new renderer

web/src/lib/
├── sections/types.ts                                # USE generated types
└── validators/sections.ts                           # UPDATE Zod schemas

web/src/components/template-creator/
└── ...                                              # USE the new manifest schema
```

### Phase 3 — cutover

```
DELETE:
- api/app/services/renderer/ir.py
- api/app/services/renderer/types.py
- api/app/services/renderer/backends/
- api/app/services/renderer/section_renderers/ (replaced by builders/)
- web/src/components/sections/*/Renderer.tsx (8 files)
- web/src/components/sections/SectionPreviewPanel.tsx
- web/src/lib/sections/fieldStyles.ts (or rewrite as FieldDef registry)
- web/src/components/sections/SectionStyle, FieldStyle interfaces

MERGE feat/ast-pipeline into master via regular merge commit.

VERIFY: pytest, npm run lint, npm run test, npm run build all pass.
```

## The schema (from the FEAT entry)

```python
class TextStyle(BaseModel):
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    color: str | None = None
    link: str | None = None
    font_size: Literal["xs", "small", "normal", "large", "xl"] | None = None

class SubsectionStyle(BaseModel):
    text_align: Literal["left", "right", "center", "justify"] | None = None
    spacing_before: str | None = None
    spacing_after: str | None = None
    background_color: str | None = None

class DateStyle(BaseModel):
    key: str
    range_sep: str = "–"

class LayoutHints(BaseModel):
    font_family: str | None = None
    date_style: DateStyle | None = None
    break_before: bool = False
    keep_together: bool = True
    heading_keeps_with_first: bool = True
    orphans: int = 2
    widows: int = 2

class SectionPolicy(BaseModel):
    show_title: bool = True
    skill_variant: Literal["block", "inline"] | None = None

class DocumentLayoutHints(BaseModel):
    page_style: str = "A4"
    break_before_first_section: bool = False
    default_orphan_threshold: int = 2
    default_widow_threshold: int = 2

class DocumentStyles(BaseModel):
    accent_color: str | None = None
    body_font: str | None = None
    heading_font: str | None = None
    default_text_align: Literal["left", "right", "center", "justify"] | None = None

class TextRun(BaseModel):
    text: str
    style: TextStyle = Field(default_factory=TextStyle)
    link: str | None = None

class FieldBlock(BaseModel):
    field_key: str
    runs: list[TextRun] = Field(default_factory=list)
    subsection_style: SubsectionStyle | None = None

class Entry(BaseModel):
    id: str
    fields: list[FieldBlock] = Field(default_factory=list)
    subsection_style: SubsectionStyle | None = None
    keep_together: bool = True

class Section(BaseModel):
    type: str
    id: str
    title: str
    enabled: bool = True
    entries: list[Entry] = Field(default_factory=list)
    layout_hints: LayoutHints = Field(default_factory=LayoutHints)
    subsection_style: SubsectionStyle | None = None
    section_policy: SectionPolicy = Field(default_factory=SectionPolicy)

class Document(BaseModel):
    page_style: DocumentLayoutHints = Field(default_factory=DocumentLayoutHints)
    global_styles: DocumentStyles = Field(default_factory=DocumentStyles)
    sections: list[Section] = Field(default_factory=list)
```

Plus the wire-shape carriers:

```python
class SectionInstance(BaseModel):
    id: str
    type: str
    title: str
    enabled: bool = True
    data: list[dict[str, Any]] | dict[str, Any] = Field(default_factory=dict)
    layout_hints: LayoutHints = Field(default_factory=LayoutHints)
    subsection_style: SubsectionStyle | None = None
    section_policy: SectionPolicy = Field(default_factory=SectionPolicy)

class ZoneStyle(BaseModel):
    width: str | None = None
    background_color: str | None = None
    padding: str | None = None

class Zone(BaseModel):
    id: str
    label: str | None = None
    styles: ZoneStyle = Field(default_factory=ZoneStyle)

class LayoutConfig(BaseModel):
    zones: list[Zone] = Field(default_factory=list)
    placement: dict[str, str] = Field(default_factory=dict)

class LayoutDefaults(BaseModel):
    spacing: Literal["compact", "comfortable", "minimal"] = "comfortable"

class PolicyOverrides(BaseModel):
    skills: dict[str, Any] | None = None

class DocumentLayout(BaseModel):
    page_style: str = "A4"
    break_before_first_section: bool = False
    default_orphan_threshold: int = 2
    default_widow_threshold: int = 2

class Customizations(BaseModel):
    global_styles: DocumentStyles = Field(default_factory=DocumentStyles)
    layout: LayoutConfig = Field(default_factory=LayoutConfig)
    layout_defaults: LayoutDefaults = Field(default_factory=LayoutDefaults)
    document_layout: DocumentLayout = Field(default_factory=DocumentLayout)
    flags: dict[str, bool] = Field(default_factory=dict)

class TemplateManifest(BaseModel):
    manifest_version: Literal[2] = 2
    name: str
    description: str | None = None
    zones: list[Zone] = Field(default_factory=list)
    placement: dict[str, str] = Field(default_factory=dict)
    layout_defaults: LayoutDefaults = Field(default_factory=LayoutDefaults)
    policy_overrides: PolicyOverrides = Field(default_factory=PolicyOverrides)
    global_styles: DocumentStyles = Field(default_factory=DocumentStyles)
    document_layout: DocumentLayout = Field(default_factory=DocumentLayout)
    section_schema: dict[str, Any] = Field(default_factory=dict)
    assets: dict[str, Any] = Field(default_factory=dict)
```

## The seed templates (minimal)

```python
SEED_TEMPLATES = [
    {
        "id": "generic-modern",
        "name": "Modern",
        "manifest_version": 2,
        "layout_defaults": {"spacing": "comfortable"},
        "policy_overrides": {},
        "zones": [{"id": "sidebar", "styles": {"width": "30%", "background-color": "#f8fafc", "padding": "24px"}},
                  {"id": "main", "styles": {"width": "70%", "padding": "24px"}}],
        "placement": {"profile": "sidebar", "experience": "main", "education": "main",
                       "skills": "main", "projects": "main", "languages": "main",
                       "certifications": "main", "research": "main"},
        "global_styles": {"accent_color": "#2563eb",
                          "body_font": "Inter, system-ui, sans-serif",
                          "heading_font": "Inter, system-ui, sans-serif"},
    },
    {
        "id": "generic-classic",
        "name": "Classic",
        "manifest_version": 2,
        "layout_defaults": {"spacing": "compact"},
        "policy_overrides": {},
        "zones": [{"id": "main", "styles": {"width": "100%", "padding": "32px"}}],
        "placement": {"profile": "main", "experience": "main", "education": "main",
                       "skills": "main", "projects": "main", "languages": "main",
                       "certifications": "main", "research": "main"},
        "global_styles": {"accent_color": "#1f2937",
                          "body_font": "Georgia, serif",
                          "heading_font": "Georgia, serif"},
    },
    {
        "id": "generic-minimal",
        "name": "Minimal",
        "manifest_version": 2,
        "layout_defaults": {"spacing": "minimal"},
        "policy_overrides": {},
        "zones": [{"id": "main", "styles": {"width": "100%", "padding": "48px"}}],
        "placement": {"profile": "main", "experience": "main", "education": "main",
                       "skills": "main", "projects": "main", "languages": "main",
                       "certifications": "main", "research": "main"},
        "global_styles": {"accent_color": "#000000",
                          "body_font": "system-ui, sans-serif",
                          "heading_font": "system-ui, sans-serif"},
    },
]
```

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

## The merge

The branch is `feat/ast-pipeline`. The merge is a regular merge commit (not squash). The branch's commit history is preserved on master. The merge is the cutover.

## Start

Begin with Phase 1.1: create `api/app/schema/models.py` with the schema above. Then the codegen script. Then the resolve. Then the renderer. The phase order is in the EPIC.

Always read the docs first. The architecture is committed to in writing. The implementation is the code that follows the architecture.

## Three things to not do

1. **Don't reimplement Python logic in TypeScript.** The codegen bridge is for types only. Runtime logic stays on the backend.
2. **Don't add backward compatibility shims.** The old code dies on the merge. No `X_LEGACY` shims, no `_resolve_legacy_*` functions, no "preserve old behavior" tests.
3. **Don't squash the merge.** The branch's commit history is preserved on master.

## The two things to do

1. **Read the docs.** AGENTS.md, PLAN.md, TEMPLATE_GUIDE.md. The EPIC + FEAT + ADRs link them together.
2. **Commit incrementally.** Each commit is independently buildable. The branch's history tells the story of the new system being built.
