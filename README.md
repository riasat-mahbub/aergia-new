# Aergia CV Builder

A single-user CV builder. FastAPI + React, HTML-first rendering.
The Python HTML renderer produces both the live preview and the PDF;
the React tree is the editor surface, never the renderer.

## What it does

Sign in, edit a CV in a schematic editor (sections, fields, no
direct HTML), pick a template, customize per-CV, export to PDF.
Three system templates ship: **modern** (two-column with sidebar),
**classic** (compact single-column), **minimal** (loose single-column).
All three render through the same HTML-first pipeline; the
difference is the manifest, not a separate renderer.

## Quick start (dev)

```bash
git clone <repo>
cd aergia
./dev.sh                # SQLite + uvicorn :8000 --reload + Vite :5173
# open http://localhost:5173
```

For a prod-like run (no Vite, frontend served by FastAPI):
`./dev.sh --build`. For the full hardening gate: `./dev.sh --smoke`.

## Architecture

```
cv.sections (JSONB wire AST, Pydantic)            # api/app/schema/models.py
  → build_document(cv, manifest)                  # services/renderer/builders/ dispatch by type
  → Document
  → resolve(document, renderer, manifest, customizations)  # pure; no I/O
  → RenderModel                                   # fully resolved; no defaults remain
  → HTMLDocumentRenderer.render(model)            # almost stupid; emits HTML
  → HTML5 + CSS
  → html_to_pdf() via Playwright Chromium        # /render/pdf, /cvs/{id}/export/pdf
```

The renderer is HTML. PDF is HTML rendered by Chromium. The React
tree mirrors the AST but never generates HTML — it is a *schematic*
editor; visual cues (e.g. page-break markers) indicate structural
intent, not literal layout. Templates express taste; renderers
express behavior. Both surfaces (live preview and PDF) call the
same renderer; the only divergence is `strip_anchor_hrefs` on the
preview path, which neutralizes `<a href>` so the sandboxed iframe
can't navigate away while editing.

## Templates

Templates are JSON manifests. The renderer reads a manifest and
emits HTML; the CSS is applied via variables defined in the
renderer's stylesheet. The user customizes the CV through the
customize panel; the customizations cascade with the template
defaults.

### Manifest schema (v2)

```json
{
  "manifest_version": 2,
  "name": "Modern",
  "description": "Two-column layout with accent color header and light sidebar",
  "zones": [
    {"id": "sidebar", "styles": {"width": "narrow", "padding": "comfortable", "background": "#f8fafc"}},
    {"id": "main",    "styles": {"width": "full",    "padding": "comfortable"}}
  ],
  "placement": {
    "profile": "sidebar",
    "experience": "main",
    "education": "main",
    "skills": "main",
    "projects": "main",
    "languages": "main",
    "certifications": "main",
    "research": "main"
  },
  "layout_defaults": {"spacing": "comfortable"},
  "policy_overrides": {"by_type": {}},
  "global_styles": {
    "accent_color": "#2563eb",
    "body_font": "Inter, system-ui, sans-serif",
    "heading_font": "Inter, system-ui, sans-serif",
    "default_text_align": "left"
  }
}
```

### Top-level keys

- **`zones`** — list of layout regions. Each has an `id` (referenced by `placement`) and `styles` (CSS properties applied to the zone wrapper). Width and padding use closed-tokens: `narrow | half | full | auto` for width; `none | tight | comfortable | loose | spacious` for padding.
- **`placement`** — map from section type (or instance ID) to zone ID. The resolver places sections into zones via this map.
- **`layout_defaults`** — template's taste. `spacing` is one of `compact | comfortable | minimal`; the resolver maps it to CSS variables (`--spacing-section`, `--spacing-subsection`).
- **`policy_overrides.by_type`** — per-type structural rules layered over the renderer defaults. Examples: `{"skills": {"skill_variant": "inline"}}` (render Skills as inline text instead of chips), `{"research": {"entry_layout": "two-column"}}` (split research entries into a 2-col grid with date+link on the right).
- **`global_styles`** — defaults for global styles, overridden by the user in the customize panel: `accent_color`, `body_font`, `heading_font`, `default_text_align`.

### Renderer cascade

The resolver layers in this order: **renderer defaults → manifest
defaults → user customizations → per-section overrides**. The
renderer receives a fully resolved `RenderModel` and emits HTML
without further decision logic.

## Project structure

```
api/        FastAPI backend (Python ≥ 3.12, Pydantic 2, SQLAlchemy 2 async, aiosqlite, Alembic)
web/        React 19 + Vite 6 + Tailwind + Zustand frontend (strict TypeScript)
scripts/    smoke.sh hardening gate; codegen helpers
tracker/    project knowledge graph (file-based, ULID, managed by the `tracker` CLI)
docs/       this README's companions (per-feature implementation plans, visual diffs)
```

## Dev commands

| Command | What it does |
|---|---|
| `./dev.sh` | SQLite + uvicorn :8000 --reload + Vite :5173 |
| `./dev.sh --build` | prod-like: build frontend, serve via FastAPI |
| `./dev.sh --prod --build` | no --reload, no Vite dev server |
| `./dev.sh --smoke` | full hardening gate (tests + lint + smoke + build) |
| `cd api && .venv/bin/python -m pytest` | backend tests |
| `cd web && npm run test` | frontend tests (Vitest) |
| `cd web && npm run codegen` | regenerate `web/src/generated/schema.ts` from the Pydantic models |
| `cd web && npm run codegen:check` | drift guard (must stay green) |
| `cd api && .venv/bin/python -m ruff check .` | backend lint |
| `cd web && npm run lint` | frontend lint |

## Documentation map

| Doc | What it is | When to read |
|---|---|---|
| `AGENTS.md` | Agent guideline, architecture summary, project conventions | First read; reference for any edit |
| `DEPLOY.md` | Docker deployment, `.env`, `SECRET_KEY` | Deploying |
| `docs/plans/<date>-*.md` | Per-feature implementation plans (each one is the work that landed in a specific commit chain) | Understanding a specific shipped feature |
| `docs/profile-vs-golden.md` | Side-by-side visual diff vs `~/Downloads/CV.pdf` | Visual-diff work; flags known regressions |
| `docs/doc-audit-and-readme-plan.md` | The audit that produced this README's structure; lists which docs were removed and why | Doc maintenance |
| `tracker/README.md` | Project knowledge graph CLI | Tracking work |

## Tracking

The project uses a file-based knowledge graph in `tracker/`. The CLI
is the source of truth for what's done, in progress, planned, and
proposed. Before editing: `tracker search <topic>`. After editing:
`tracker update <id> --note "..."` and `tracker rebuild && tracker validate`.

| Folder | Type | Count |
|---|---|---|
| `tracker/bugs/` | bug | 25 |
| `tracker/features/` | feature | 58 |
| `tracker/decisions/` | adr | 5 |
| `tracker/tasks/` | task | 124 |
| `tracker/docs/` | doc | 1 |
| `tracker/epics/` | epic | 2 |

## Tracking conventions

- One commit per task; commit message follows `feat(…): …` / `fix(…): …` / `tracker: …` style.
- Every commit carries a tracker update (`tracker new` / `tracker update` + `tracker rebuild && tracker validate`) so the tracker never drifts from the branch.
- Feature work merges into `master` via a regular merge commit (not squash); the merge is the cutover.
