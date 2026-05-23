# Aergia CV Builder — Agent Guide

## Tracker

Bugs, features, decisions, tasks, and docs are tracked as individual markdown
files in `tracker/` (project-tracker SCHEMA 3, ULID IDs).  See
`tracker/README.md` for the dashboard and migration history.

| Folder | DONE | OPEN | Total |
|--------|------|------|-------|
| [bugs/](tracker/bugs/) | 9 | 0 | 9 |
| [features/](tracker/features/) | 19 | 10 | 29 |
| [decisions/](tracker/decisions/) | 3 | 0 | 3 |
| [tasks/](tracker/tasks/) | 8 | 14 | 22 |
| [docs/](tracker/docs/) | 0 | 1 | 1 |

**Last updated:** 2026-08-01 (from `tracker stats`)

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
- **Sections**: The data model uses `SectionInstance[]` — an array of self-contained section objects with `id`, `type`, `title`, `enabled`, and `data`. Multiple instances of the same type allowed. See `PLAN.md:107-155`.

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
