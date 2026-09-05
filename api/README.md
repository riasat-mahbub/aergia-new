# Aergia API

The `api/` service is a FastAPI application. It owns authentication, CVs,
applications, the reusable Library, templates, assets, rendering, imports,
and tailoring-session endpoints.

## Code map

```text
app/routes/                HTTP adapters under /api/v1
app/services/              business operations and validation
app/document_schema/       document AST, manifests, and render model
app/http_schemas/          HTTP request/response DTOs
app/models/                SQLAlchemy tables
app/services/renderer/     pure builders/resolver plus HTML/PDF runtime
alembic/                   database migrations
scripts/codegen_schema.py  Pydantic → TypeScript generator
tests/                     pytest checks
```

The document renderer is HTML-first. The React editor does not render the
export document; both preview and PDF use the Python HTML renderer.

## Local development

From the repository root, run `./dev.sh` for SQLite, FastAPI on `:8000`, and
the Vite web server on `:5173`. FastAPI's development documentation is
available through the same-origin gateway at `/api/docs`; the JSON schema is
at `/api/openapi.json`.

Useful backend commands:

```bash
source .venv/bin/activate
alembic upgrade head
pytest
ruff check .
```

Install Chromium once for PDF export with `playwright install chromium`.
