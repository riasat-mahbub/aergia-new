# Frontend boundary and SOLID refactor plan

**Date:** 2026-09-04  
**Status:** Implemented in the current working tree  
**Tracker:** `FEAT-01M1QQX2ZKE6Q05G3MKKKFRBGR`  
**Depends on:** completed page-oriented ownership refactor

## Outcome

Finish the separation started by the `src/app` migration without changing
product behavior or beginning the Next.js runtime cutover. Route-owned state
lives with its route, services expose transport operations rather than UI or
store behavior, contracts use generated CV schema types where possible, and
the route tree produces real bundle boundaries.

## Target dependency direction

```text
app route composition
  -> route-private components/hooks/stores
  -> shared components or global stores
  -> services
  -> HTTP client

pure lib -X-> React, Zustand, services, app, DOM/window/document
services -X-> React, Zustand, route components, toasts/navigation
contracts -X-> services, stores, app, components
```

Browser adapters are allowed under an explicit browser-oriented `lib` module
or provider boundary; they are not considered pure utilities.

## Phases

### Phase 1 — Pure domain and contract seams

- Split the old CV types module into schema, section data/catalog, placement,
  and date modules.
- Make `DateField` interactive-only and use the pure date module elsewhere.
- Type CV/library wire contracts with generated schema types.

### Phase 2 — Library and LLM domain ownership

- Move library vocabulary into `lib/library/catalog.ts` and dashboard-only
  grouping selectors into the library route.
- Split LLM contracts, provider metadata/detection, and the memory-only
  `store/llmKeyStore.ts`; remove duplicate UI provider lists.

### Phase 3 — Route-owned CV state

- Move dashboard list/create/copy/delete state to
  `app/dashboard/_stores/cvListStore.ts`.
- Move active Builder document/loading/save state to
  `app/builder/[id]/_stores/builderDocumentStore.ts` and remove the old mixed
  global CV store.

### Phase 4 — Service purity and browser adapters

- Keep API services transport-only; move blob downloads to
  `lib/browser/downloadBlob.ts`.
- Pass import credentials explicitly from the caller and move unauthorized
  browser cleanup/redirect into `ClientProviders`.
- Keep render request/response types in the builder route types module.

### Phase 5 — Builder orchestration decomposition

- Add pure Builder document commands for section mutations.
- Extract document loading/migration, save/dirty lifecycle, and template
  manifest/switching hooks.
- Extract `BuilderHeader` and `BuilderWorkspace`; keep route composition in the
  page and use React Router params.

### Phase 6 — Route component decomposition

- Extract the Builder sortable row and delete dialog.
- Extract application detail job, relevance, generated-CV/tailoring, status
  history, linked-CV loading, and pure form normalization seams.

### Phase 7 — Rich-text subsystem seams

- Split selection traversal, formatting, link commands, and selection-state
  logic into focused modules.
- Extract `LinkDialog` and link application commands while leaving the
  bidirectional Lexical codec cohesive.

### Phase 8 — Route loading and enforceable architecture

- Use React Router route-level lazy imports and preserve the loading fallback.
- Extend the boundary checker with pure-lib, contract, service, store, and
  shared-component dependency rules plus fixture tests.
- Update repository guidance and stale comments to final paths.

## Verification matrix

Run after each phase:

```bash
cd web
npm run architecture:test
npm run architecture:check
npm run lint -- --quiet
npm run codegen:check
npm run build
```

The backend date parity test was attempted during Phase 1 but the existing
pytest setup did not produce output and was interrupted; no backend behavior
was changed.

## Deferred work

- Actual Next.js installation, Server/Client Component conversion, Next
  navigation blocking, and deployment topology.
- Broad visual redesign or splitting cohesive rendering/codec algorithms only
  to satisfy a line-count target.
