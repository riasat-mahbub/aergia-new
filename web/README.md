# Aergia web app

The `web/` service is the TanStack Start/React editing application. It serves
the UI and the same-origin `/api/*` gateway while FastAPI remains the private
upstream.

## Code map

```text
src/routes/       route adapters and URL/search/SSR ownership
src/features/     product capabilities and feature-local pages
src/shared/       reusable UI, API, CV, browser, and state helpers
src/generated/    generated TypeScript schema (do not edit)
src/middleware/   Start security middleware
server/           Nitro same-origin API gateway
```

To understand a screen, start at its file in `src/routes/`, then follow the
feature named by its import. Shared code should be useful to more than one
feature.

## Local development

From `web/`, run `npm install` and `npm run dev` (Vite uses `:5173` and
proxies `/api` to FastAPI on `:8000`). From the repository root,
`./dev.sh` starts both services. Production-like builds use `npm run build`.

Run `npm run architecture:check` after moving files and
`npm run codegen:check` after backend schema changes.
