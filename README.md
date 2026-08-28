# Aergia CV Builder

A single-user CV builder. You sign in, edit a CV in a schematic
editor, pick a template, customize the look, and export to PDF. The
whole app is one FastAPI process serving a React SPA; the same
HTML-first renderer drives both the live preview and the PDF.

## What you get

- **Schematic editor.** A panel-based editor where you add sections
  (Experience, Education, Projects, Research, Skills, Languages,
  Certifications) and fill in fields. No raw HTML, no formatting
  toolbar — the editor mirrors the data model.
- **Three system templates** that share the same renderer:
  - **Modern** — two-column with a narrow sidebar (profile + skills)
    and a wide main column for everything else.
  - **Classic** — single-column, compact spacing.
  - **Minimal** — single-column, loose spacing.
- **Customize panel** for per-CV adjustments: accent color, fonts,
  heading divider, per-section spacing. Edits are live in the
  preview.
- **PDF export** via Chromium print, with real clickable link
  annotations on the URLs you provide.

## How it works (the user-facing flow)

```
                  ┌──────────────────────────────────────────────┐
                  │                                              │
   sign in ──────►│  Dashboard (list of CVs)                    │
                  │                                              │
                  └────────────────┬─────────────────────────────┘
                                   │  open / new
                                   ▼
                  ┌──────────────────────────────────────────────┐
                  │                                              │
                  │  Builder page                                │
                  │  ┌──────────────┐  ┌──────────────────────┐  │
                  │  │ Section list │  │  Live preview        │  │
                  │  │ • Experience │  │  ┌────────────────┐  │  │
                  │  │ • Education  │  │  │  Same HTML the  │  │  │
                  │  │ • Projects   │  │  │  PDF uses       │  │  │
                  │  │ • Research   │  │  └────────────────┘  │  │
                  │  │ • Skills     │  │  (sandboxed iframe)   │  │
                  │  └──────────────┘  └──────────────────────┘  │
                  │  ┌──────────────┐                            │
                  │  │ Customize    │  ← accent color, fonts,   │
                  │  │ panel        │    per-section spacing     │
                  │  └──────────────┘                            │
                  └────────────────┬─────────────────────────────┘
                                   │  click "Export PDF"
                                   ▼
                  ┌──────────────────────────────────────────────┐
                  │                                              │
                  │  PDF download                                │
                  │  • Page-sized HTML rendered by Chromium     │
                  │  • Real clickable URLs as link annotations   │
                  │  • Same content as the preview               │
                  │                                              │
                  └──────────────────────────────────────────────┘
```

The preview and the PDF are **the same render** — what you see is
what you get. No "export will look slightly different" surprises.

## The data flow (what happens when you save)

When you change a field, here's the round trip:

```
   ┌──────────┐    save     ┌──────────────────┐
   │  React   │────────────►│  POST /cvs/{id}   │
   │  editor  │             │  (FastAPI)        │
   └──────────┘             └────────┬─────────┘
       ▲                            │
       │  GET /cvs/{id} (re-render)  │
       │  or PATCH                   ▼
       │                  ┌──────────────────┐
       │                  │  Validate via     │
       │                  │  Pydantic schema  │
       │                  └────────┬─────────┘
       │                           │
       │                           ▼
       │                  ┌──────────────────┐
       │                  │  Save to          │
       │                  │  SQLite (JSONB)   │
       │                  └────────┬─────────┘
       │                           │
       │   preview / export         ▼
       │                  ┌──────────────────┐
       └──────────────────│  Re-render via    │
                          │  the renderer     │
                          └──────────────────┘
```

The CV is stored as JSON in SQLite. Each save round-trips through
Pydantic validation, so invalid data (missing required fields,
wrong types) is rejected at the boundary.

## How a CV becomes a PDF

This is the part the rest of the system hangs off:

```
   CV (JSONB)                                    Template (manifest)
       │                                                │
       │   ┌─────────────────────┐                    │
       └─►│  build_document(cv)   │                    │
          │  (one builder per      │                    │
          │   section type)        │                    │
          └──────────┬────────────┘                    │
                     │                                 │
                     ▼                                 │
          ┌─────────────────────┐                    │
          │  Document (typed     │                    │
          │  AST)                │                    │
          └──────────┬──────────┘                    │
                     │                                 │
                     │     ┌──────────────────────────┘
                     │     │
                     ▼     ▼
          ┌─────────────────────┐
          │  resolve(document,   │
          │  renderer,           │
          │  manifest,           │
          │  customizations)     │
          │                      │
          │  Apply:              │
          │  • manifest defaults │
          │  • user customizations│
          │  • per-section       │
          │    overrides         │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │  RenderModel         │
          │  (fully resolved;    │
          │   no defaults left)  │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │  HTMLDocumentRenderer│
          │  .render(model)      │
          │  → HTML5 + CSS       │
          └──────────┬──────────┘
                     │
                     ├──────────────┐
                     │              │
                     ▼              ▼
          ┌──────────────┐  ┌────────────────────┐
          │  Live preview│  │  html_to_pdf()      │
          │  (sandboxed  │  │  via Playwright     │
          │   iframe)    │  │  Chromium           │
          └──────────────┘  └─────────┬──────────┘
                                        │
                                        ▼
                                  ┌──────────┐
                                  │  PDF     │
                                  └──────────┘
```

The renderer is **almost stupid** — it reads the resolved model and
emits HTML. No decisions, no defaults, no "what does the user want".
Every choice is made upstream, in the resolver. This is what keeps
the preview and the PDF identical.

The live preview and the PDF share everything **except one step**: the
preview neutralizes `<a href>` to `#` so the sandboxed iframe can't
navigate away while you edit. The PDF keeps the real hrefs, so
Chromium's print engine produces clickable link annotations.

## Templates

A template is a JSON manifest — a small file that declares the
template's taste. The renderer reads it; the CSS values it produces
are the manifest's choices.

```json
{
  "manifest_version": 2,
  "name": "Modern",
  "description": "Two-column layout with accent color header and light sidebar",
  "zones": [
    {"id": "sidebar", "styles": {"width": "narrow", "padding": "comfortable"}},
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
    "heading_font": "Inter, system-ui, sans-serif"
  }
}
```

### What each key means

- **`zones`** — layout regions with their width/padding. `narrow`
  is about a third, `half` is half, `full` is the rest.
- **`placement`** — which section types go in which zone. The
  "modern" template puts profile + skills in the sidebar, everything
  else in main.
- **`layout_defaults.spacing`** — `none | compact | comfortable | minimal`.
  Sets the gap between sections and between fields.
- **`policy_overrides.by_type`** — per-section overrides of
  renderer defaults. Example: `{"skills": {"skill_variant": "inline"}}`
  renders the skills section as one line of text instead of chips.
- **`global_styles`** — accent color, body and heading fonts.
  These are the defaults; the customize panel lets you override
  them per CV.

The resolver layers everything in this order: **renderer defaults →
manifest defaults → user customizations → per-section overrides**.
The renderer never has to think.

## Customizing a CV

The customize panel sits alongside the editor. It exposes three
groups, one per style axis:

```
   ┌─────────────────────────────┐
   │  Section policy              │
   │  ◻ Show title               │
   │  ◻ Heading divider           │
   │  Skills layout: [Default ▼]  │  ← per-type override
   │                              │
   │  Subsection                  │
   │  Text align: [left ▼]        │
   │                              │
   │  Layout                      │
   │  Font family: [sans ▼]       │
   └─────────────────────────────┘
```

Each control writes to the CV's customization object, which the
resolver merges with the template defaults. Edits are live — the
preview re-renders on every change.

## Getting started

### Run it locally (development)

```bash
git clone <repo>
cd aergia
./dev.sh                # SQLite + uvicorn :8000 --reload + Vite :5173
# open http://localhost:5173
```

`./dev.sh` brings up:
- A SQLite database at `data/aergia.db` (auto-created, no setup)
- The FastAPI backend on `:8000` with auto-reload
- The Vite dev server on `:5173` (proxies `/api` → `:8000`)

Open `http://localhost:5173` and the app is running.

For a production-like run (no Vite dev server, frontend served by
FastAPI from `web/dist`):

```bash
./dev.sh --build
```

For the full hardening gate (tests + lint + smoke + production build
+ live render check):

```bash
./dev.sh --smoke
```

### Deploy

See [`DEPLOY.md`](DEPLOY.md) for the Docker + `.env` + domain setup.

## Project structure

```
api/         FastAPI backend (Python ≥ 3.12, Pydantic, SQLAlchemy 2 async, aiosqlite, Alembic)
web/         React 19 + Vite 6 + Tailwind + Zustand frontend
docs/        Per-feature plans, visual diffs against the golden CV
tracker/     Project knowledge graph (what's done, planned, proposed)
dev.sh       Single command to bring the whole stack up
```

## Common dev commands

| Command | What it does |
|---|---|
| `./dev.sh` | SQLite + backend (`:8000`, reload) + Vite (`:5173`) |
| `./dev.sh --build` | Production-like: built frontend served by FastAPI |
| `./dev.sh --smoke` | Full hardening gate (tests + lint + smoke + build) |
| `cd api && .venv/bin/python -m pytest` | Backend tests |
| `cd web && npm run test` | Frontend tests |
| `cd web && npm run codegen` | Regenerate `web/src/generated/schema.ts` from the Pydantic models |
| `cd web && npm run codegen:check` | Drift guard — must stay green in CI |
| `cd api && .venv/bin/python -m ruff check .` | Backend lint |

## Where to go next

- **Deploying?** Read [`DEPLOY.md`](DEPLOY.md).
- **Want to add a new section type?** The Pydantic models in
  `api/app/schema/models.py` are the source of truth. Add the
  field shape, write a builder in `api/app/services/renderer/builders/`,
  add a TS type via `npm run codegen`, and the editor + preview +
  PDF all light up automatically.
- **Want to add a new template?** Write a manifest (see the schema
  above), drop it in the seed, and the three system-template slots
  in the template picker populate on next start.
- **Tracking what's done or planned?** The project uses a
  file-based knowledge graph in `tracker/`. The CLI is the source
  of truth — see [`tracker/README.md`](tracker/README.md).
- **Visual regression against a reference PDF?**
  [`docs/profile-vs-golden.md`](docs/profile-vs-golden.md) is the
  current side-by-side comparison.
