# Frontend guide

The web app uses TanStack Start/Router, React 19, Vite, Tailwind, strict
TypeScript, and Zustand.

## Directory ownership

- `src/routes/` contains every TanStack route file. A route reads URL params
  and search values, owns redirects/SSR settings, and passes plain props to a
  feature page.
- `src/features/<name>/` owns one product capability. Keep code in named
  `pages/`, `components/`, `hooks/`, `domain/`, `api/`, `state/`, or `types/`
  directories when that distinction helps. Each feature has an explicit
  `index.ts` public entrypoint.
- `src/shared/` contains code used by several features: API client, browser
  adapters, CV schema facade and pure helpers, CV editors, form hooks,
  rich-text codecs, security helpers, UI, and global UI state.
- `src/generated/schema.ts` is codegen output. Import it through
  `shared/cv/schema.ts`; never hand-edit it.
- `src/middleware/` and `src/server` contain Start request/security plumbing.

There is no `src/app/` directory and no top-level `pages/` directory. A
feature-local `pages/` directory is fine when a feature has multiple screens.

## Dependency direction

```text
routes → feature public entrypoints → shared
features → their own internals, other feature public entrypoints, shared
shared -X→ features and routes
```

Do not deep-import another feature. Keep `domain/` free of React, Zustand,
Axios, UI, API, state, route modules, and browser globals. Keep `api/` free of
UI/pages/hooks/state. Keep `state/` free of UI/pages. Only
`shared/api/client.ts` configures Axios.

The architecture checker and fixture suite enforce these rules:

```bash
npm run architecture:test
npm run architecture:check
```

## Route and rendering notes

The editor is schematic. The preview is a sandboxed iframe produced by the
FastAPI HTML renderer, and PDF export uses the same HTML through Chromium.
Do not add a second React export renderer.

Keep the public `/agent/tailor/$sessionId` route unchanged. The tailoring
feature receives its `sessionId` from the route adapter.

## Commands

```bash
npm install
npm run dev
npm run build
npm run lint
npm run typecheck
npm run codegen:check
```
