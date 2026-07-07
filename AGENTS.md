# Aergia CV Builder — Agent Guide

## Tracker

Bugs, features, decisions, tasks, and docs are tracked as individual markdown
files in `tracker/` (project-tracker SCHEMA 3, ULID IDs).  See
`tracker/README.md` for the dashboard and migration history.

| Folder | Type | Total |
|--------|------|-------|
| [bugs/](tracker/bugs/) | bug | 17 |
| [features/](tracker/features/) | feature | 56 |
| [decisions/](tracker/decisions/) | adr | 5 |
| [tasks/](tracker/tasks/) | task | 118 |
| [docs/](tracker/docs/) | doc | 1 |
| [epics/](tracker/epics/) | epic | 2 |

**Status** (from `tracker stats`, 2026-08-08): DONE 107 · IN_PROGRESS 20 · PLANNED 50 · PROPOSED 22 · 199 entries total.

**Last updated:** 2026-08-08 (from `tracker stats`)



## Required skill: project-tracker

This project uses a file-based project knowledge graph in tracker/.
- Before editing: search for related entries (`tracker search <topic>`)
- After editing: update entries and rebuild (`tracker update <id> --status ... --note "..."`, `tracker rebuild && tracker validate`)

## Quick start

```bash
./dev.sh                          # SQLite + uvicorn --reload (:8000) + Vite dev (:5173)
./dev.sh --build                  # Prod-like: build frontend, serve via FastAPI only
./dev.sh --prod --build           # No --reload, no Vite dev server
```

Frontend dev server proxies `/api` → `localhost:8000` (configured in `web/vite.config.ts:9`).

## Project structure

```
api/          FastAPI + SQLAlchemy async + Alembic    Entry: api/app/main.py → app.py
web/          React 19 + Vite 6 + Tailwind + Zustand  Entry: web/src/main.tsx
```

The FastAPI app at `:8000` serves both the API (`/api/v1/*`) and the built SPA (`/*` SPA fallback at `app.py:92`). No reverse proxy needed.

## Key commands

### Backend (api/)
```bash
cd api && source .venv/bin/activate
pip install -e ".[test]"
alembic upgrade head
pytest                                      # All tests
pytest tests/test_auth.py -k "full_flow"    # Single test
ruff check .                                # Lint (line-length=120)
```

### Frontend (web/)
```bash
npm install
npm run dev          # Vite dev server :5173
npm run build        # tsc -b && vite build
npm run test         # Vitest (all)
npm run lint         # ESLint
```

## Testing quirks

- **Backend**: uses `httpx.AsyncClient` with `ASGITransport`, not FastAPI's `TestClient`. See `tests/conftest.py`. `pytest-asyncio` mode is `auto` (configured in `pyproject.toml:42`) — no `@pytest.mark.asyncio` decorators needed.
- **Frontend**: Vitest with jsdom environment, `@testing-library/jest-dom` in `web/src/lib/test/setup.ts`. Globals enabled.
- Integration tests use the actual DB (seeded per session, templates created on app startup).

## Architecture notes

- **Single-origin**: CORS only allows `frontend_url` (defaults to `localhost:8000`). No CORS needed in Docker/production.
- **Auth**: bcrypt cost 12, JWT HS256. Access token = 15min, refresh = 7d. Refresh tokens stored as SHA-256 hashes in DB. Tokens stored in Zustand (localStorage). Auto-hydration on mount via `useAuthStore.hydrate()` in `App.tsx:17`.
- **DB**: Async SQLAlchemy 2.0 + aiosqlite. Session auto-commits on success, rolls back on error (`session.py:16-23`). SQLite with `check_same_thread=False` for async access. Single file at `data/aergia.db`. No Docker needed for local dev.
- **Templates**: 3 seed templates (modern, classic, minimal) seeded on each startup (`seed.py` — idempotent, checks existence). Data stored as JSONB in `cvs.sections` and `cvs.customizations`.
- **PDF export**: Uses Playwright (Chromium, headless, singleton browser). Must be installed: `playwright install chromium`. Browser is reused across requests, closed on app shutdown via lifespan event (`pdf.py:18-45`).
- **Rate limiting**: slowapi with 100 req/min global, 10 req/min on auth routes.
## Architecture promise

The new system (Phase 7) is HTML-first:

- **Canonical rendering target is HTML + CSS.** The preview iframe, the PDF export, and any future HTML-based output all go through the same Python HTML renderer.
- **PDF export is HTML rendered by Chromium.** Not a separate engine.
- **The React tree is the editor surface, not a renderer.** It does not produce HTML for the preview or PDF. The preview and PDF are produced by the Python HTML renderer.
- **Editor is schematic, not rendered.** The editor visualizes the document structure (sections, fields, brackets); the PDF visualizes the computed layout. The editor does not promise to show the exact spacing, page breaks, or font fallbacks the PDF will produce. Visual cues (e.g., "page break" markers) indicate structural intent without literal page boundaries.
- **Templates express taste; renderers express behavior.** Seed templates declare `layout_defaults: { spacing: comfortable }`. The renderer maps to CSS variables; the stylesheet defines the values. Templates don't override CSS values directly.

## Render model discipline

- **Logic stays on the backend.** Pydantic models are data shapes, not logic containers. Validation lives in the service layer, not as Pydantic methods. The frontend never validates data shapes; it asks the backend for validation results.
- **Codegen is for types only.** Generated TypeScript files (in `generated/`) are never edited manually. CI checks that running `datamodel-code-generator` produces no diff. If TS wrapper code reimplements Python validator logic, that's a design smell — extract it to a shared runtime module or move the logic to the backend.
- **Three orthogonal axes for styling:**
  - `TextStyle` — inline per-field appearance (bold, italic, color, font-size, link).
  - `SubsectionStyle` — block-level appearance per section/entry (text_align, spacing, background_color).
  - `LayoutHints` — page flow and structural intent (break_before, keep_together, orphans, widows, font_family, date_style).
  - `SectionPolicy` is document semantics. The HTML renderer implements policy with HTML constructs.

## Renderer capabilities

Every renderer declares its own `RendererSupport` (property of the renderer class). The customize panel reads the active renderer's support. The export endpoint reads the renderer's support. The renderer is the source of truth for what it can do.

Each capability field has a `SupportLevel`:
- `FULL` — the renderer reliably satisfies this; the control is shown normally.
- `BEST_EFFORT` — the renderer tries but can't guarantee; the control is shown with a warning icon.
- `NONE` — the renderer can't satisfy this; the control is hidden.

## Merge policy

The new branch merges into `master` via a regular merge commit (not squash). The branch's commit history is preserved on `master`. The merge is the cutover: the old code is gone in one step.

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

The React tree mirrors the AST but doesn't render HTML. The Python HTML renderer is the document renderer. Both consume the same data; the rendering is different.


## Architectural Decisions (ADRs)

- **2026-05-01: Manifest-driven templates** — Replaced the dual-pipeline
  (hard-coded React renderers + HTML user templates) with a single manifest
  JSON schema. Every template is defined by 4 artefacts: manifest.json,
  template.html, styles.css, optional assets. The visual editor writes the
  manifest; HTML/CSS are derived artefacts. See `tracker/decisions/ADR-01KYZ1XG6W0K8NQPMV2Z6WCVYM-adr-manifest-driven-templates.md`.
- **2026-06-27: Manual save over auto-save** — Auto-save had 3 rounds of bug
  fixes for race conditions. Replaced with explicit manual save (Save button,
  Ctrl+S, save-on-navigate blocker, unsaved indicator). Simpler mental model.
  See `tracker/decisions/ADR-01KYZ1XG9EWRX1VXY30CRCTMJH-adr-manual-save-over-auto-save.md`.
- **2026-07-26: PostgreSQL → SQLite migration** — Replaced PostgreSQL/asyncpg
  with SQLite/aiosqlite for zero-dependency local dev. Removed Docker requirement
  for development. Simpler backups (single file). Lost concurrent write capability
  but acceptable for single-user CV builder. See `tracker/decisions/ADR-01KYZ1XGGHXX9F2DW5HDXBBWMG-adr-postgresql-sqlite-migration.md`.

## Conventions

- **Ruff**: line-length 120, target py312.
- **TypeScript**: strict mode, `noUnusedLocals: true`, `noUnusedParameters: true`.
- **CSS**: Tailwind utility classes. No CSS modules beyond template-specific styles.
- **State**: Zustand stores in `web/src/lib/store/`. Auth store auto-hydrates from localStorage.
- **Docker build context** is repo root (`.`), not `api/` — the Dockerfile needs both `api/` and `web/`.

## Gotchas

- `alembic.ini` has a hardcoded SQLite URL; the app overrides it from `DATABASE_URL` env var at runtime (`alembic/env.py:16-18`).
- Backend tests use SQLite (no Docker needed). Tests seed templates before each run via conftest (`conftest.py:8-18`).
- The SPA catch-all route uses `/{full_path:path}` — this can conflict if you add new API routes that are not under `/api/v1/`.
- Playwright browsers install to `~/.cache/ms-playwright` locally, `/app/ms-playwright` in Docker.
- `SECRET_KEY` default `change-me-in-production` raises a `RuntimeError` in production mode.

## Phase 2 status (2026-08-07)

The customize panel writes only the three-axis `SectionInstanceStyle`
(`style.layout / .subsection / .policy / .text[key]`). The per-CV
`Customizations` is canonical (no legacy `{colors, fonts, spacing,
flags}` keys) — those legacy keys are now rejected at the model
boundary. `/render/support` returns the renderer's capability map;
the panel gates per-control visibility on those values.

Components deliberately stubbed in Phase 2 — to be rebuilt in Phase 3:
- `web/src/components/template-creator/TemplateWizard.tsx` (deprecated banner)
- `web/src/components/customization/StyleEditor.tsx` (deleted; was the wizard's editor)

Trackers: `FEAT-01KZJ0PHASE2QA-phase-2-three-axis-customize-panel`,
`BUG-01KZJ0PHASE2QA-customizations-wire-mismatch`,
`BUG-01KZJ0PHASE2QA-template-wizard-on-legacy-paths`,
`TASK-01KZJ0PHASE2QA-phase-3-template-creator-and-global-customizations`.

Full plan: `'/home/riasat/.omp/agent/sessions/-Projects-aergia/2026-08-07T01-11-42-848Z_019fd9c6-a800-7000-a163-80d19cc593e9/local/ast-pipeline-phase-2-plan-v5.md'`.

## Phase 3 status (2026-08-07)

Phase 3 rebuilt the template creator and added a global customizations
editor. The new `TemplateWizard` is a four-step wizard (Basics / Layout /
Global Styles / Review). It writes the v2 `TemplateManifest` shape and is
gated by `templateManifestSchema` before save. The customize panel's
"Document" disclosure writes per-CV `Customizations.accent_color / body_font /
heading_font / spacing` — the only top-level customizations the user
can author in this phase. Legacy `default_customizations` is no longer
written.

Full plan: see Phase 2 plan above.

## Phase 4 status (2026-08-08)

Phase 4 replaced the legacy `{colors, fonts, spacing, flags}` shape and
the free-form CSS strings on `ZoneStyle` with a typed closed
vocabulary. The manifest exposes a constrained design vocabulary:
`WidthToken | SpacingToken | FontToken | ColorRef (hex literal or
palette.<name>)`. Raw CSS strings are no longer accepted at the
schema boundary. The resolver is the only place tokens become CSS
values; it imports renderer-defined token and palette tables from
`app/services/renderer/palette.py` and `tokens.py`.

Drag-drop zone authoring and per-instance policy overrides (which
Phase 4 noted as deferred) are shipped in Phase 6.

Full plan: `local://ast-pipeline-phase-4-plan-v2.md`.

## Phase 5 status (2026-08-08)

Phase 5 replaced the resolver's hard-coded `HTMLDocumentRenderer.support`
fallback with a required `DocumentRenderer` parameter. `resolve(document, renderer, manifest, customizations) -> RenderModel` is now renderer-agnostic; `HTMLDocumentRenderer` is constructed once per request. The codegen script auto-discovers `BaseModel` subclasses via `inspect.getmembers`, removing the hand-maintained whitelist; `api/tests/test_codegen.py` asserts every `BaseModel` subclass is emitted. `api/tests/test_resolve.py` introduces the `FakeRenderer` test double proving the protocol is consumable. Phase 5 shipped the renderer protocol contract that the future DOCX renderer will plug into.

Full plan: `local://phase-5-renderer-protocol-and-codegen-plan.md`.

## Phase 6 status (2026-08-08)

Phase 6 deleted the user-template authoring surface (`TemplateWizard`, `TemplateCreatorPage`, `BaseTemplateCard`, `TemplateLayoutView`, `userTemplateStore`, the `/api/v1/templates/user` routes, the multipart `/api/v1/templates` upload, and the user-templates section of `TemplateSelectorModal`). The `Template.is_system` and `Template.user_id` columns were dropped via Alembic migration. The customize panel is now the sole styling surface and writes only canonical `SectionInstanceStyle` plus canonical top-level `Customizations`. Phase 6 also closed drag-drop zone authoring end-to-end (`BuilderPage.handleLayoutConfigChange.test.tsx` round trip) and per-instance `SectionPolicy` overrides (`resolve.py` now respects an existing `section.policy` rather than clobbering it with the type default).

Full plans: `local://phase-6-content-only-authoring-plan.md`, `local://phase-6-step-2-prompt.md`.

## Phase 7 status (2026-08-08)

Phase 7 is closed. The HTML-first pipeline with the three-axis style AST shipped across Phases 1–6. The umbrella epic `EPIC-01KZCCC3MTXDGPY31H06NFYP1Q-html-first-pipeline-with-three-axis-style-ast` is closed through `EPIC-01KZHRBNQPZDMWFH7MQPAW5BBG`. Post-Phase-7 invariants and the architecture promise are recorded in `local://phase-7-ast-pipeline-closeout.md`. The original prompt is preserved in `PHASE_7_PROMPT.md` as historical record. Every existing CV with `generic-modern` / `generic-classic` / `generic-minimal` continues to render through the customize panel; the customize panel tests are unchanged.

## Phase 8 hardening status (2026-08-08)

Phase 8 is closed. The selected Phase 8 behavior is hardening rather than a new product feature. The reachable developer behavior is `./dev.sh --smoke`, which runs pytest + Ruff + source-only Vitest + ESLint + production build, then an isolated live-render smoke against `generic-modern`, `generic-classic`, and `generic-minimal` using a fresh temporary SQLite database. Vitest discovery is locked to `web/src`; `eslint-plugin-react-hooks` is pinned in `web/package.json` so `npm run lint` no longer reports `ERR_MODULE_NOT_FOUND`. Hardening touched verification, documentation, and tracker wiring only — no Pydantic schema, generated TypeScript, manifest vocabulary, resolver contract, `RenderModel`, renderer, or customize-panel payload changed.

Tracker: `TASK-01KZHR806TYQPTPEFG5JE8879C-phase-8-hardening-gate`. Plan: `local://phase-7-closeout-phase-8-hardening-plan.md`. Closeout: `local://phase-7-ast-pipeline-closeout.md`.
