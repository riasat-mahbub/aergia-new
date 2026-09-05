# Repository Guidelines

Aergia is a single-user CV builder. The repository contains a FastAPI service,
a TanStack Start/React web app, an HTML-first document renderer, and the
portable tailoring skill used by coding agents.

## Read the closest instructions first

When work touches a subsystem, read its local guide before editing:

- `api/AGENTS.md` for the backend and renderer.
- `web/AGENTS.md` for the frontend.
- `tailoring-skill/AGENTS.md` for the agent workflow and contracts.

Rules in a closer `AGENTS.md` apply to that subtree. When starting from the
repository root, do not assume the root guide contains subsystem details.

## Architecture that must stay true

- The canonical document path is Pydantic AST → pure resolver → resolved
  render model → Python HTML → Chromium PDF. React is the editing surface;
  it is not a second renderer.
- The public web server is TanStack Start on port `3000`. It owns the same
  origin `/api/*` gateway. FastAPI is the private upstream on port `8000`.
- Frontend route registration belongs only in `web/src/routes/`. Product
  capabilities belong in `web/src/features/`. Reusable cross-feature code
  belongs in `web/src/shared/`.
- A feature's `index.ts` is its public entrypoint. Routes and other features
  must not import another feature's internal files. Shared code must not
  import features or routes.
- `api/app/document_schema/` is the document AST and renderer model.
  `api/app/http_schemas/` contains HTTP request and response DTOs.
- `tailoring-skill/` contains the local skill, protocol contracts, tools, and
  tests. The browser URL `/agent/tailor/$sessionId` is stable.

## Safe implementation workflow

1. Search the tracker before editing: `tracker search "topic"` and
   `tracker affects <id>`.
2. Keep product behavior, public URLs, API payloads, database shape, and
   editor settings unchanged unless the task explicitly changes them.
3. Use `apply_patch` for hand edits. Use ordinary file moves or mechanical
   replacements only for a clearly bounded rename/move.
4. Keep generated files generated. After document-model changes run
   `cd web && npm run codegen:check` (run `npm run codegen` when needed).
5. Update the tracker after the work, then run `tracker rebuild && tracker
   validate`. Existing fork warnings are documented tracker warnings; do not
   hide or rewrite unrelated history.

## Main checks

```bash
./dev.sh --smoke
cd api && .venv/bin/pytest
cd ../web && npm run lint && npm run typecheck && npm run architecture:test
cd ../web && npm run architecture:check && npm run codegen:check
node --test tailoring-skill/tests/*.test.mjs
```

The smoke gate is the release check. Focused frontend behavior tests are a
follow-up; the architecture fixture suite is the current frontend structure
guard.

## Change boundaries

- Keep secrets, access tokens, and tailoring capabilities out of files and
  logs.
- Keep validation in backend services; schema modules describe data shapes.
- Keep database sessions async and let route dependencies manage commit or
  rollback. Services flush but do not commit.
- Reuse the Playwright singleton for PDF work and close it during app shutdown.
- Merge feature work into `master` with a regular merge commit; the merge is
  the cutover.
