# Aergia CV Builder — Active Plan

**Last updated:** 2026-06-27  
**Scope:** Manifest-first template system rewrite with visual step-by-step editor.

---

## Vision

Replace the current dual-pipeline template system (hard-coded system templates + HTML-only user templates) with a **single manifest-driven pipeline** where:

1. **Every template** (system or user) is defined by the same 4 artefacts: `manifest.json`, `template.html`, `styles.css`, optional assets.
2. **The visual editor is the source of truth** — it writes the manifest; HTML/CSS are *derived* artefacts.
3. **One renderer** (IR → HTML / PDF) serves both preview and export, extensible to LaTeX/DOCX later.
4. **System templates** are merely seeded manifest rows with `is_system=true` (delete-protected, grouped in UI).

---

## 5-Phase Roadmap

| Phase | Goal | Est. Effort | Status |
|-------|------|-------------|--------|
| **1 – Frontend Cleanup** | Extract reusable UI, simplify existing components so the coming editor rewrite starts from a clean base. | ~1 week | ✅ **DONE** |
| **2 – Manifest Data Model & Upload** | Define the on-disk/DB representation, multipart upload API, and DB migration. | ~1 week | ✅ **DONE** |
| **3 – New Renderer (IR → HTML / PDF)** | Build a pure-function pipeline that consumes manifest + CV data with pluggable back-ends. | ~2 weeks | ⏳ |
| **4 – Preview & PDF** | Wire the new renderer into front-end preview (`UserTemplateRenderer`) and the PDF service. | ~1 week | ⏳ |
| **5 – Visual Template Creator** | Replace the two-tab creator with a guided manifest-centric wizard. | ~2 weeks | ⏳ |

**Total:** ~7 weeks

---

## Phase 1 – Frontend Cleanup (Independent, Do First) ✅ **COMPLETED**

*Extracted from old Phase 3 to reduce noise before the big rewrite.*

| # | Task | Files | Status |
|---|------|-------|--------|
| 1.1 | Create `StyleEditor.tsx` (global colors/fonts/spacing) | `web/src/components/customization/StyleEditor.tsx` | ✅ |
| 1.2 | Create `ZonesSection.tsx` (zone layout accordion + `ZoneLayoutBar`) | `web/src/components/customization/ZonesSection.tsx` | ✅ |
| 1.3 | Refactor `CustomizePanel.tsx` → use `StyleEditor` + `ZonesSection` | `web/src/components/customization/CustomizePanel.tsx` | ✅ |
| 1.4 | Refactor `TemplateCustomizePanel.tsx` → use shared components | `web/src/components/template-creator/TemplateCustomizePanel.tsx` | ✅ |
| 1.5 | **Remove vertical row-height drag** from `ZoneLayoutBar` | `web/src/components/customization/ZoneLayoutBar.tsx` | ✅ |
| 1.6 | Add `normalizeAllZones()` helper to `zones.ts`; use in 6 handlers | `web/src/lib/sections/zones.ts`, `ZoneLayoutBar.tsx` | ✅ |
| 1.7 | Collapse `validateSection.ts`: profile / `SECTION_TYPES` array / default | `web/src/lib/validators/validateSection.ts` | ✅ |
| 1.8 | Run `npm run lint && npm run test` — zero regressions | — | ⏳ (pre-existing test mock issue) |

**Deliverable:** Clean, deduplicated customization UI; `ZoneLayoutBar` slimmed to horizontal resize only.

---

## Phase 2 – Manifest Data Model & Upload ✅ **COMPLETED**

### 2.1 Manifest Schema (`manifest.json`)

```json
{
  "version": 1,
  "id": "generic-modern",
  "name": "Modern",
  "description": "Two-column layout with accent color header and light sidebar",
  "zones": [
    { "id": "sidebar", "row": 0, "styles": { "width": "30%", "background-color": "#f8fafc", "padding": "24px" }, "label": "Sidebar" },
    { "id": "main", "row": 0, "styles": { "width": "70%", "padding": "24px" }, "label": "Main" }
  ],
  "placement": {
    "profile": "sidebar",
    "experience": "main",
    "education": "main",
    "skills": "main",
    "projects": "main",
    "languages": "main",
    "certifications": "main"
  },
  "globalStyleSchema": [
    { "key": "accent", "type": "color", "label": "Accent", "default": "#2563eb" },
    { "key": "bg_sidebar", "type": "color", "label": "Sidebar BG", "default": "#f8fafc" },
    { "key": "header", "type": "color", "label": "Header", "default": "#000000" },
    { "key": "divider", "type": "color", "label": "Divider", "default": "#d1d5db" },
    { "key": "text", "type": "color", "label": "Text", "default": "#374151" },
    { "key": "heading", "type": "color", "label": "Heading", "default": "#111827" },
    { "key": "body_font", "type": "font", "label": "Body Font", "default": "Inter, system-ui, sans-serif" },
    { "key": "heading_font", "type": "font", "label": "Heading Font", "default": "Inter, system-ui, sans-serif" },
    { "key": "section_gap", "type": "length", "label": "Section Gap", "default": "24px" }
  ],
  "assets": {
    "font-inter": "fonts/Inter.woff2"
  },
  "sectionSchema": {
    "profile": { "fields": ["name","title","email","phone","location","summary","photo_url"] },
    "experience": { "fields": ["company","position","start_date","end_date","current","location","description"] },
    ...
  }
}
```

* `globalStyleSchema` lets **users declare their own style variables** (type = `color|font|length|enum`). The visual editor builds the StyleEditor UI from this schema.
* `assets` maps logical names → relative paths inside the template bundle.
* **`rowHeights` removed** — row height is now content-driven; only row order matters.

### 2.2 Database Changes

| Table | Change |
|-------|--------|
| `templates` | Add `manifest JSONB`, `assets JSONB` columns. Legacy columns (`layout_template`, `layout_config`, `default_customizations`) kept for compatibility; they are now **derived** from manifest on read. |
| `templates` | Keep `is_system BOOLEAN DEFAULT false`, `user_id UUID FK` (NULL for system). |

### 2.3 Upload API

```
POST /api/v1/templates          (multipart)
  - manifest.json (required)
  - template.html (optional – generated if missing)
  - styles.css    (optional – generated if missing)
  - assets/*      (optional)
Response: TemplateDetail with generated HTML/CSS preview URLs
```

* Server validates manifest against a Pydantic model, generates missing `template.html`/`styles.css` via `manifest_to_layout_template`, stores blobs.

### 2.4 Seed System Templates

Run a one-off script that converts the three existing seed templates into manifest rows (`is_system=true`). No migration of user data needed (clean DB for dev/staging).

### 2.5 Tasks

| # | Task | Status |
|---|------|--------|
| 2.1 | Write `Manifest` Pydantic model + JSON Schema | ✅ |
| 2.2 | Alembic migration: add `manifest`, `assets` columns | ✅ |
| 2.3 | `POST /templates` multipart endpoint with validation + generation | ✅ |
| 2.4 | `GET /templates/{id}/manifest` (raw) + `GET /templates/{id}/html` (generated) | ✅ |
| 2.5 | Seed script for 3 system templates | ✅ |
| 2.6 | Update `TemplateDetail` schema to include manifest + generated URLs | ✅ |
| 2.7 | Integration tests: upload manifest → fetch generated HTML → render preview | ⏳ |

---

## Phase 3 – New Renderer (IR → HTML / PDF)

### 3.1 Package Layout

```
api/app/services/renderer/
├── __init__.py              # exports: render_html, render_pdf
├── ir.py                    # build_intermediate_representation(manifest, cv_data, customizations) → IR
├── html.py                  # ir_to_html(ir) → complete HTML5 string
├── pdf.py                   # ir_to_pdf(ir) → bytes (Playwright)
├── section_renderers/
│   ├── __init__.py          # SECTION_RENDERERS dict
│   ├── profile.py
│   ├── experience.py
│   ├── education.py
│   ├── skills.py
│   ├── projects.py
│   ├── languages.py
│   └── certifications.py
├── css_vars.py              # substitute_css_vars, merge_customizations
├── placeholders.py          # replace_unknown_zones (3 helpers)
└── types.py                 # IR dataclasses, shared types
```

### 3.2 Intermediate Representation (IR)

```python
@dataclass
class ZoneIR:
    id: str
    styles: dict[str, str]          # resolved CSS (width, background-color, padding…)
    panels: list[SectionPanelIR]    # ordered, already rendered HTML strings

@dataclass
class SectionPanelIR:
    type: str
    title: str
    html: str
    wrapper_style: str
    heading_style: str

@dataclass
class DocumentIR:
    zones_by_row: dict[int, list[ZoneIR]]
    row_heights: dict[int, str]     # "60%", "40%" …
    css_vars: dict[str, str]        # --accent, --body-font, …
    print_styles: str
    body_font: str
    heading_font: str
```

`ir.py` does **all logic**: grouping sections by zone via `placement`, normalising widths per row, resolving CSS vars, building section HTML via `section_renderers`. It is **pure** (no I/O, no side-effects).

### 3.3 Back-ends

* **HTML back-end** (`html.py`) → emits complete HTML5 with `{{print_styles}}`, `{{body_font}}`, `{{heading_font}}` placeholders already substituted.
* **PDF back-end** (`pdf.py`) → `page.setContent(html)` → `page.pdf(format="A4", margin={"top":0,"bottom":0,"left":0,"right":0})`. Re-uses `html.py`.

**Interface for future back-ends:**

```python
class RendererBackend(Protocol):
    def render(self, ir: DocumentIR) -> bytes | str: ...
```

### 3.4 Tasks

| # | Task |
|---|------|
| 3.1 | Create `renderer/` package skeleton |
| 3.2 | Extract 7 section renderers into `section_renderers/` |
| 3.3 | Move `_group_instances_by_zone`, `_render_zones`, `_build_zone_styles` → `ir.py` |
| 3.4 | Move `_substitute_css_vars`, `_merge_customizations` → `css_vars.py` |
| 3.5 | Split `_replace_unknown_zones` → `placeholders.py` (3 pure functions) |
| 3.6 | Implement `build_ir(manifest, cv_data, customizations)` in `ir.py` |
| 3.7 | Implement `ir_to_html(ir)` in `html.py` |
| 3.8 | Implement `ir_to_pdf(ir)` in `pdf.py` (Playwright) |
| 3.9 | Wire `render_html` / `render_pdf` in `__init__.py` |
| 3.10 | Update `api/app/services/pdf.py` to call new `render_pdf` |
| 3.11 | Unit tests: IR builder, HTML output, PDF bytes for all 3 system templates |

---

## Phase 4 – Preview & PDF Integration

| # | Task |
|---|------|
| 4.1 | `TemplateSwitcher.tsx` → always fetch template manifest (if not in context) and render `UserTemplateRenderer` with generated `layout_template` + `layout_config` + `default_customizations`. |
| 4.2 | `UserTemplateRenderer.tsx` → call **new HTML back-end** via a tiny server endpoint (`POST /api/v1/render/html { manifest, cv_data, customizations }`) or a WASM port of `html.py`. Simpler: keep current iframe + `renderUserTemplateHTML` **but** point it at the new Python renderer via a preview endpoint. |
| 4.3 | Delete `ModernTemplate.tsx`, `ClassicTemplate.tsx`, `MinimalTemplate.tsx`. |
| 4.4 | `BaseTemplateCard.tsx` thumbnail → generate from manifest `zones` (mini SVG zone diagram). |
| 4.5 | `CustomizePanel.tsx` → drop `isUserTemplate` guard; global style controls work for every template because every manifest has `globalStyleSchema`. |
| 4.6 | `BuilderPage.tsx` → ensure it passes `templateLayoutConfig` (now derived from manifest) and `templateDefaultCustomizations` to `TemplateSwitcher`. |
| 4.7 | PDF export (`api/app/services/pdf.py`) → calls new `render_pdf`. |
| 4.8 | Integration tests: preview + PDF for system templates + a sample user template. |

---

## Phase 5 – Visual Template Creator (Step-by-Step Wizard)

Replace the current two-tab (`Design` / `HTML`) creator with a **guided 4-step wizard** that writes the manifest directly.

### 5.1 Wizard Steps

| Step | UI Component | Manifest Fields Written |
|------|--------------|------------------------|
| **1 – Layout** | `ZoneLayoutBar` (rows, zones, drag-resize, placement) | `zones`, `placement`, `rowHeights` |
| **2 – Global Styles** | `StyleEditor` **built from** `globalStyleSchema` (user can add/remove variables, pick type) | `globalStyleSchema`, `default_customizations` |
| **3 – Assets (optional)** | Drag-drop zone for fonts / images → stored in `assets` map | `assets` |
| **4 – Review** | Read-only generated HTML preview (calls `layoutConfigToHTML` + injects current `default_customizations`) | — |

**Save** → `POST /api/v1/templates` multipart (manifest + generated HTML/CSS + assets). System templates stay read-only (`is_system` only used for UI grouping & delete protection).

### 5.2 Picker UI (`TemplateCreatorPage`)

```
┌─────────────────────────────────────┐
│  System Templates (read-only)       │  ← grouped by is_system=true
│  ┌─────┐ ┌─────┐ ┌─────┐           │
│  │Modern│ │Classic│ │Minimal│ ...  │  ← thumbnails GENERATED from manifest
│  └─────┘ └─────┘ └─────┘           │
├─────────────────────────────────────┤
│  Your Templates (editable)          │  ← grouped by is_system=false
│  ┌─────┐ ┌─────┐                   │
│  │My CV│ │Clean │ ...              │
│  └─────┘ └─────┘                   │
└─────────────────────────────────────┘
```

### 5.3 Tasks

| # | Task |
|---|------|
| 5.1 | Build `TemplateWizard` component (stepper + step components) |
| 5.2 | Step 1: embed `ZoneLayoutBar` (horizontal resize only) |
| 5.3 | Step 2: dynamic `StyleEditor` driven by `globalStyleSchema` editor (add/remove variables) |
| 5.4 | Step 3: asset drop-zone (optional) |
| 5.5 | Step 4: live generated HTML preview |
| 5.6 | `POST /templates` upload on wizard completion |
| 5.7 | Update `TemplateCreatorPage` → wizard replaces Design/HTML tabs |
| 5.8 | `BaseTemplateCard` thumbnail generator from manifest |
| 5.9 | Delete old `TemplateCustomizePanel`, `TemplateCreatorPage` two-tab logic |
| 5.10 | Rewrite `TEMPLATE_GUIDE.md` to match new manifest + wizard workflow |
| 5.11 | E2E test: create template via wizard → use in builder → export PDF |

---

## Future / Out of Scope (Do Not Append as Phases)

- Desktop Tauri 2.x wrapper (`desktop/`)
- LaTeX / DOCX renderer back-ends (interface ready in Phase 3)
- Per-section style override tests (T11.2–T11.5)
- Migration of existing user templates (clean DB, re-upload)

---

## Reference: Key Files to Touch

| Area | Files |
|------|-------|
| Frontend UI (Phase 1) | `web/src/components/customization/*.tsx`, `web/src/lib/sections/zones.ts`, `web/src/lib/validators/validateSection.ts` |
| Manifest model & API (Phase 2) | `api/app/models/template.py`, `api/app/schemas/template.py`, `api/app/routes/templates.py`, `api/app/db/seed.py`, new migration |
| Renderer (Phase 3) | New `api/app/services/renderer/` package |
| Preview / PDF (Phase 4) | `web/src/components/preview/*.tsx`, `api/app/services/pdf.py`, `api/app/routes/cvs.py` |
| Template Creator (Phase 5) | `web/src/pages/TemplateCreatorPage.tsx`, new `web/src/components/template-creator/TemplateWizard.tsx` |
| Docs | `TEMPLATE_GUIDE.md` (rewrite) |

---

## Success Criteria

1. **Single render path** – `render_preview` / `render_pdf` identical for system & user templates.
2. **Zero hard-coded template components** – `ModernTemplate.tsx` etc. deleted.
3. **Visual editor is source of truth** – HTML/CSS are generated artefacts.
4. **User-defined global styles** – schema lives in manifest, UI built dynamically.
5. **Clean test suite** – all integration tests pass for preview + PDF on all templates.

---

*End of active plan. Completed work archived in COMPLETED.md.*