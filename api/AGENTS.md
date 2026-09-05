# Backend guide

FastAPI backend for Aergia. Python 3.12+, SQLAlchemy 2 async, aiosqlite,
Alembic, Pydantic v2, slowapi, and Playwright.

## Directory ownership

- `app/app.py` wires the FastAPI application, middleware, routers, and
  lifespan.
- `app/document_schema/` is the single source of truth for the document AST,
  wire AST, template manifests, customization models, and `RenderModel`.
- `app/http_schemas/` contains thin HTTP request/response models. Do not put
  service validation or renderer decisions in these modules.
- `app/models/` contains SQLAlchemy ORM models.
- `app/routes/` contains HTTP adapters. Business rules live in `app/services/`.
- `app/services/renderer/` is pure except for the HTML renderer and its
  Playwright runtime. `resolve()` and builders do not access the database.
- `scripts/codegen_schema.py` emits `web/src/generated/schema.ts`; never edit
  that generated file by hand.

## Data and rendering rules

The rendering flow is:

```text
CV JSON AST → build_document() → resolve() → RenderModel
→ HTMLDocumentRenderer → HTML → Chromium PDF
```

Templates use the closed v2 token vocabulary. Only the resolver converts
tokens into CSS values. Renderer capabilities come from `RendererSupport` and
are returned by `/api/v1/render/support`; do not hard-code capabilities in a
route or frontend control.

Use async SQLAlchemy sessions. Routes use `get_db()` for commit/rollback;
services call `flush()` and never call `commit()` themselves. Reuse the
Playwright singleton in `services/renderer/_pdf_runtime.py`.

## HTTP and security

- Routers are mounted below `/api/v1`.
- Development and test expose Swagger at `/api/docs` and OpenAPI JSON at
  `/api/openapi.json`. ReDoc is disabled. Production disables both docs URLs.
- Every operation has one OpenAPI tag. Keep the tag list in `app/app.py`
  ordered and update it when adding a router.
- Auth uses secure cookies, CSRF checks, bcrypt, JWT rotation, and slowapi
  limits. Do not log passwords, tokens, API keys, or tailoring capabilities.
- Production rejects the default secret and unsafe token settings.

## Commands

```bash
source .venv/bin/activate
alembic upgrade head
pytest
ruff check .
python scripts/codegen_schema.py --check
```

Run a focused test while iterating, for example
`.venv/bin/pytest -q tests/test_openapi.py`. Use the repository smoke gate for
the full same-origin and security flow.
