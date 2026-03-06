# Aergia CV Builder — Agent Guide

## Quick start

```bash
./dev.sh                          # Docker Postgres + uvicorn --reload (:8000) + Vite dev (:5173)
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

- **Backend**: uses `httpx.AsyncClient` with `ASGITransport`, not FastAPI's `TestClient`. See `tests/conftest.py`. All integration tests need `@pytest.mark.asyncio`. `pytest-asyncio` mode is `auto` (configured in `pyproject.toml:42`).
- **Frontend**: Vitest with jsdom environment, `@testing-library/jest-dom` in `web/src/lib/test/setup.ts`. Globals enabled.
- Integration tests use the actual DB (seeded per session, templates created on app startup).

## Architecture notes

- **Single-origin**: CORS only allows `frontend_url` (defaults to `localhost:8000`). No CORS needed in Docker/production.
- **Auth**: bcrypt cost 12, JWT HS256. Access token = 15min, refresh = 7d. Refresh tokens stored as SHA-256 hashes in DB. Tokens stored in Zustand (localStorage). Auto-hydration on mount via `useAuthStore.hydrate()` in `App.tsx:17`.
- **DB**: Async SQLAlchemy 2.0 + asyncpg. Session auto-commits on success, rolls back on error (`session.py:16-23`).
- **Templates**: 3 seed templates (modern, classic, minimal) seeded on each startup (`seed.py` — idempotent, checks existence). Data stored as JSONB in `cvs.sections` and `cvs.customizations`.
- **PDF export**: Uses Playwright (Chromium, headless, in-process). Must be installed: `playwright install chromium`.
- **Rate limiting**: slowapi with 100 req/min global, 10 req/min on auth routes.
- **Sections**: The data model uses `SectionInstance[]` — an array of self-contained section objects with `id`, `type`, `title`, `enabled`, and `data`. Multiple instances of the same type allowed. See `PLAN.md:107-155`.

## Conventions

- **Ruff**: line-length 120, target py312.
- **TypeScript**: strict mode, `noUnusedLocals: true`, `noUnusedParameters: true`.
- **CSS**: Tailwind utility classes. No CSS modules beyond template-specific styles.
- **State**: Zustand stores in `web/src/lib/store/`. Auth store auto-hydrates from localStorage.
- **Docker build context** is repo root (`.`), not `api/` — the Dockerfile needs both `api/` and `web/`.

## Gotchas

- `alembic.ini` has a hardcoded localhost URL; the app overrides it from `DATABASE_URL` env var at runtime (`alembic/env.py:16-18`).
- Backend tests need Postgres running (start via `dev.sh` or `docker compose up -d postgres`).
- The SPA catch-all route uses `/{full_path:path}` — this can conflict if you add new API routes that are not under `/api/v1/`.
- Playwright browsers install to `~/.cache/ms-playwright` locally, `/app/ms-playwright` in Docker.
- `SECRET_KEY` default `change-me-in-production` raises a `RuntimeError` in production mode.
