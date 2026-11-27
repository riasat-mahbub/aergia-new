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

Use the Python launcher from the repository root on Windows, macOS, or Linux
with Python 3.12 or later and Node.js with npm. Use `python3` if that is the
Python command on your system.

```text
python dev.py           # Vite on port 5173 with API reload
python dev.py --build   # Build and serve TanStack Start on port 3000
python dev.py --prod    # Serve an existing build with API reload disabled
python dev.py --smoke   # Lint, build, and check both services with a temporary database
```

Use `--build --prod` to build before starting in production mode. The smoke
check uses the local virtual environment and installed frontend dependencies.
Install Ruff 0.12.12 in `api/.venv`, or set `AERGIA_SMOKE_RUFF` to the path
of a compatible Ruff executable.

On the first serving run, dependency setup and the Chromium download can take
several minutes. Open the URL printed on the `Frontend` line after startup.
Keep the launcher running to serve the app. The smoke check stops both
servers when it finishes.

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
