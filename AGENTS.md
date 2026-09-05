# Repository Guidelines

Aergia CV Builder — a single-user CV builder: FastAPI backend (`api/`) serving a React 19 SPA (`web/`) plus the document render pipeline. Rendering is **HTML-first**: the Python HTML renderer produces both the preview and the PDF; the React tree is the editing surface, not a renderer.

## Project Overview

- **Stack**: FastAPI + SQLAlchemy 2.0 async + aiosqlite + Alembic (Python ≥ 3.12); React 19 + Vite 6 + Tailwind + Zustand (strict TypeScript).
- **Single-origin**: the FastAPI app on `:8000` serves both `/api/v1/*` and the built SPA at `/*` (SPA catch-all `/{full_path:path}`). In dev, Vite on `:5173` proxies `/api` → `localhost:8000` (`web/vite.config.ts:9-13`). No reverse proxy.
- **HTML-first pipeline**: canonical rendering target is HTML + CSS. PDF export is that HTML rendered by Chromium (Playwright singleton). The React tree mirrors the AST but never generates HTML — it is a *schematic* editor; visual cues (e.g. page-break markers) indicate structural intent, not literal layout.
- **Templates express taste; renderers express behavior.** Seed templates declare a v2 manifest with a closed token vocabulary; the resolver is the only place tokens become CSS values.
- **Merge policy**: feature work merges into `master` via a regular merge commit (not squash); the merge is the cutover.

## Architecture & Data Flow

```
cv.sections (JSONB wire AST, Pydantic)            # api/app/schema/models.py
  → build_document(cv, manifest)                  # services/renderer/builders/ dispatch by type
  → Document
  → resolve(document, renderer, manifest, customizations)   # pure, no I/O
  → RenderModel                                   # fully resolved; no defaults remain
  → HTMLDocumentRenderer.render(model)            # complete HTML5 string
  → HTML                                         # /render/html, /cvs/{id}/preview
  → html_to_pdf() via Playwright Chromium        # /render/pdf, /cvs/{id}/export/pdf
```

- **Three orthogonal style axes**: `TextStyle` (inline), `SubsectionStyle` (block), `LayoutHints` (page flow). `SectionPolicy` is document semantics, not HTML. The customize panel writes `SectionInstanceStyle` (`style.layout/.subsection/.policy/.text`) plus top-level `Customizations` (`accent_color`, `body_font`, `heading_font`, `spacing`).
- **Capability gating**: every renderer declares `RendererSupport` with `SupportLevel` (`FULL` / `BEST_EFFORT` / `NONE`). `/render/support` returns the map; the customize panel gates control visibility; the resolver drops `NONE` features. The renderer is the source of truth for what it can do.
- **Codegen for types only**: `api/scripts/codegen_schema.py` (custom in-tree generator — **not** datamodel-code-generator, which was rejected for dependency issues) emits `web/src/generated/schema.ts` from every `BaseModel` in `app.schema.models` (auto-discovered via `inspect.getmembers`). Never hand-edit generated TS; `npm run codegen:check` guards drift.
- **Templates**: 3 seed templates (`generic-modern`, `generic-classic`, `generic-minimal`) with v2 manifests and closed vocabulary (`WidthToken`/`SpacingToken`/`FontToken`/`ColorRef` = hex literal or `palette.<name>`; raw CSS strings rejected at the schema boundary). Seeded idempotently on app startup (`db/seed.py`).

## Key Directories

```
api/
  app/
    app.py            # FastAPI app: lifespan, CORS (non-prod), security headers, router mounts, SPA fallback
    main.py           # entry: re-exports `app` from app.py
    config.py         # pydantic-settings Settings, reads .env
    schema/models.py  # SINGLE SOURCE OF TRUTH: Pydantic AST + wire + manifest + RenderModel
    schemas/          # thin HTTP request/response models (auth, cv, photo)
    models/           # SQLAlchemy ORM (user, cv, template)
    db/               # session.py (async engine + get_db), seed.py (idempotent template seeding)
    core/             # auth (bcrypt/JWT), deps (get_current_user), rate_limit (slowapi)
    routes/           # auth, cvs, templates, assets, render — mounted under /api/v1
    services/         # auth, cv, pdf, photo — validation lives here
    services/renderer/  # builders/, resolve.py, html.py, base.py, support.py, palette.py, tokens.py, policy.py, _pdf_runtime.py
  alembic/            # env.py (DATABASE_URL override) + versions/
  scripts/            # codegen_schema.py
  tests/
web/
  src/
    main.tsx          # RouterProvider entry; route modules are lazy-loaded by app/router.tsx
    app/              # route pages, layouts, providers, and route-private _components/_hooks/_lib/_services/_stores/_types
    components/       # shared section editors, controls, library cards, and preview primitives
    lib/cv/           # generated-schema facade plus pure section catalog, placement, date, and editor-data modules
    lib/library/      # pure library kind catalog
    lib/llm/          # pure provider metadata/detection; credentials live in store/llmKeyStore.ts
    lib/browser/      # explicit DOM adapters such as downloadBlob
    lib/rich-text/    # bidirectional wire/Lexical codec
    middleware/security/ # TanStack Start request security, nonce CSP, and headers
    store/            # global Zustand stores only; route-owned stores stay under their app subtree
    generated/schema.ts  # codegen output — never hand-edit
scripts/              # smoke.sh (hardening gate)
docs/plans/           # phase plans
tracker/              # file-based project knowledge graph (see Project tracker)
```

## Development Commands

```bash
./dev.sh                          # SQLite + uvicorn :8000 --reload + Vite dev :5173
./dev.sh --build                  # prod-like: build frontend, serve via FastAPI only
./dev.sh --prod --build           # no --reload, no Vite dev server
./dev.sh --smoke                  # full hardening gate (see Testing & QA)

# Backend (api/)
source .venv/bin/activate
pip install -e ".[test]"
alembic upgrade head
pytest                            # all tests
pytest tests/test_auth.py -k full_flow   # single test
ruff check .                      # lint; line-length 120, target py312

# Frontend (web/)
npm install
npm run dev                       # Vite dev server :5173
npm run build                     # tsc -b && vite build
npm run lint                      # ESLint (flat config)
npm run architecture:test        # dependency-boundary fixture checks
npm run architecture:check       # route privacy + layer direction
npm run codegen                   # regenerate web/src/generated/schema.ts
npm run codegen:check             # drift guard (must stay green)
```

## Code Conventions & Common Patterns

### Backend

- **Validation lives in the service layer**, not as Pydantic methods. Schema models are data shapes; `app.schema.models` (AST source of truth) is distinct from `app.schemas` (HTTP I/O). The schema boundary only enforces shape (e.g. `model_validator` color-ref checks, legacy `{colors, fonts}` rejection in `Customizations._reject_legacy`).
- **Session lifecycle**: routes depend on `get_db()`, which auto-commits on success and rolls back on exception (`db/session.py:21-28`). Services call `flush()`, never `commit()`.
- **Async only**: SQLAlchemy 2.0 async + async routes (`aiosqlite`, `check_same_thread=False`, `expire_on_commit=False`).
- **Renderer is pure**: `resolve()` and builders take already-validated models and do no I/O/DB; `HTMLDocumentRenderer` is "almost stupid" — no decisions or defaults.
- **Renderer is source of truth for capabilities**: extend `RendererSupport` + a renderer's `support` when adding a capability; never hard-code renderer assumptions in the resolver.
- **Manifest v2 + closed vocabulary**: templates/zone styles carry only tokens, never raw CSS strings. `_resolve_zone_styles` in the resolver is the ONLY place tokens become CSS.
- **Auth**: bcrypt cost 12, JWT HS256 (access 15 min / refresh 7 d, claims `{sub: email, exp}`), refresh tokens stored as SHA-256 hashes and rotated on refresh/logout/change-password.
- **Rate limiting**: slowapi — global `100/minute`, auth routes `10/minute`. Replaced by a no-op `TestLimiter` in test env.
- **PDF**: reuse the Playwright singleton via `services/renderer/_pdf_runtime.py`; never launch a second browser. `close_browser()` runs on app shutdown.
- **Codegen after model changes**: run `npm run codegen` (or `api/scripts/codegen_schema.py`) whenever `app/schema/models.py` changes; keep `--check` green.

### Frontend

- **Strict TS**: `strict`, `noUnusedLocals`, `noUnusedParameters`.
- **Styling**: Tailwind utility classes; no CSS modules beyond template-specific styles.
- **State**: global Zustand stores in `store/` — `authStore` hydrates from the cookie session, `llmKeyStore` is memory-only, and `uiStore` handles toasts. Dashboard CV-list state and Builder document state are route-owned stores.
- **API**: one axios client (`services/client.ts`, baseURL `/api/v1`, CSRF/401 refresh callbacks) + typed per-domain wrappers. Browser redirects and downloads live in providers/adapters.
- **Editor is schematic, not rendered**: components mirror the AST; the only rendered views are the sandboxed iframe preview (`UserTemplateRenderer.tsx`, POST `/render/html`, `PAGE_HEIGHT_PX=1122`, page-break overlay) and the PDF blob export.
- **Tests**: the previous Vitest/component suite was intentionally removed at
  the page-structure reset. Focused behavior tests remain a follow-up; the
  architecture fixture suite is run with `npm run architecture:test`.
- **Generated types**: import through `lib/cv/schema.ts` (re-exports `web/src/generated/schema.ts`); never edit the generated file.

## Important Files

| File | Why it matters |
|---|---|
| `api/app/schema/models.py` | Single source of truth: AST, wire types, manifest v2, Customizations, RenderModel. Codegen input. |
| `api/app/app.py` | App wiring: lifespan (seed templates + Playwright close), CORS, security headers, router mounts, SPA fallback. |
| `api/app/services/renderer/resolve.py` | Pure resolver — pipeline brain: cascade, CSS vars, zones, capability gating, `ManifestVersionError`. |
| `api/app/services/renderer/html.py` | `HTMLDocumentRenderer` — canonical HTML output; print styles, best-effort comments. |
| `api/app/services/renderer/support.py` | `SupportLevel` + `RendererSupport` capability map. |
| `api/scripts/codegen_schema.py` | In-tree Pydantic→TS generator; `--check` drift gate. |
| `web/src/app/builder/[id]/page.tsx` | Schematic editor orchestrator; document commands, persistence, template loading, and visual panes are route-private modules. |
| `web/src/app/builder/[id]/_components/customization/Inspector.tsx` / `SectionInspector.tsx` | Three-axis style inspector, document customizations, and capability gating. |
| `web/src/services/client.ts` | Single axios entry point for all API I/O and refresh/CSRF callbacks. |
| `web/vite.config.ts` | Dev proxy (`/api` → `:8000`) and Vite build configuration. |
| `api/alembic/env.py` | `DATABASE_URL` override (lines 22-24). `alembic.ini` hardcodes a SQLite URL that is overridden at runtime. |
| `dev.sh` / `scripts/smoke.sh` | Dev orchestrator / hardening gate. |
| `README.md` | Project entry point: what it is, quick start, architecture, templates, dev commands, doc map | First read for any new contributor |
| `DEPLOY.md` | Docker deployment, `.env`, `SECRET_KEY` | Deploying |

## Runtime/Tooling Preferences

- **Python ≥ 3.12** (`requires-python >=3.12`), venv at `api/.venv`, pip. Ruff line-length 120, target py312.
- **npm only** (`package-lock.json`; no bun/pnpm/yarn). Node version unpinned locally; Docker builds use `node:20-alpine`.
- **Playwright Chromium required for PDF export**: `playwright install chromium`. Browsers cache to `~/.cache/ms-playwright` locally, `/app/ms-playwright` in Docker.
- **SECRET_KEY**: default `change-me-in-production` raises `RuntimeError` when `environment=production`.
- **No CI workflows exist** (no `.github/`). The de-facto gate is `./dev.sh --smoke`. Qlty config (`.qlty/qlty.toml`: bandit, hadolint, osv-scanner, radarlint, ruff, shellcheck, trufflehog) is separate from CI.
- **Docker**: build context is the repo root (`.`), not `api/` — the `api/Dockerfile` needs both `api/` and `web/`; SPA is copied to `/app/static`.
- **Database**: single SQLite file at `data/aergia.db`; no Docker needed for local dev. Backend tests use a dedicated `aergia.test.db`.

## Testing & QA

Two independent stacks; no coverage gate on either side (pytest-cov installed but unconfigured; no coverage script in `web/package.json`).

### Backend — legacy pytest checks (`api/tests/`)

- Keep a legacy test only when it passes unchanged and still exercises current
  behavior. A test that requires rewriting belongs in the deferred test-suite
  rebuild; a test that exposes a genuine application regression remains valid.
- Retained API tests use `httpx.AsyncClient` over `ASGITransport` (not
  FastAPI `TestClient`).
- Fresh fixtures, browser flows, and migration-specific coverage are deferred
  to the replacement test suite.

### Frontend checks (`web/`)

- The previous Vitest/component suite was intentionally removed at the
  page-structure reset and is not currently configured. Focused behavior tests
  remain a follow-up once route boundaries settle.
- `npm run architecture:test` exercises prohibited dependency edges with
  temporary fixtures; `npm run architecture:check` validates the real tree.

### Migration smoke gate — `./dev.sh --smoke`

Runs Ruff + frontend ESLint + production build, then an isolated live
TanStack Start/FastAPI smoke against a temporary SQLite database. It checks
Start SSR, nonce-based CSP/security headers, the same-origin API gateway,
root-scoped auth cookies, login, refresh rotation, and logout. It intentionally
does not claim comprehensive behavioral test coverage; that suite is deferred.
The Alembic bootstrap is bounded by `AERGIA_SMOKE_MIGRATION_TIMEOUT_SECONDS`
(default 30 seconds) so runtime/database compatibility failures are reported
instead of hanging the gate.

## Project tracker

This project uses a file-based project knowledge graph in `tracker/` (SCHEMA 3, ULID IDs). See `tracker/README.md` for the dashboard and CLI reference (`search`, `affects`, `new`, `update`, `close`, `reopen`, `history`, `rebuild`, `validate`, `stats`). Live stats (2026-08-10): 228 entries — DONE 129 · IN_PROGRESS 20 · PLANNED 51 · PROPOSED 28 (bugs 26 · features 58 · tasks 136 · adr 5 · docs 1 · epics 2).

## Required skill: project-tracker

This project uses a file-based project knowledge graph in tracker/.
- Before editing: search for related entries (`tracker search <topic>`)
- After editing: update entries and rebuild (`tracker update <id> --status ... --note "..."`, `tracker rebuild && tracker validate`)
