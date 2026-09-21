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

Use `scanner-pdf-smoke` to check the Playwright driver, Chromium launch, Aergia's
HTML-to-PDF renderer, and pdfplumber recovery independently. A missing browser
binary is an installation issue; Chromium's `Operation not permitted` launch
failure means the process sandbox blocks browser startup and must be corrected
in the runtime that hosts the API. Some managed development runners block
Chromium syscalls even when both the Playwright driver and browser binary are
installed; run this diagnostic in the API runtime that will perform PDF work.
Scanner semantic, lexical, and presentation results remain available when PDF
rendering is unavailable.
