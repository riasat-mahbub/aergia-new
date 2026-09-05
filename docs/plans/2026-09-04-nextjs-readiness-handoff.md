# Handoff: directly migrate the frontend to `src/app`

**Date:** 2026-09-04
**Audience:** The next planning/implementation agent
**Status:** Route-private service/store/contract separation is implemented; the actual Next.js runtime/deployment cutover remains planned and separately gated.

## Decision summary

Move the existing routed page implementations into `web/src/app/` and make
that tree the canonical owner of the application routes. Do not create thin
page adapters and do not keep a duplicate `features/<page>` screen layer.

The Builder is a top-level authenticated route at `/builder/:id`, separate
from the dashboard URL namespace. During the Vite stage it still uses the
dashboard shell for auth, navigation, and the Back to CVs action; the Next
cutover must give this route an equivalent layout or route-group layout.

The frontend will use explicit boundaries for reusable code:

- `services/` owns API access and application operations.
- `store/` owns global client state and calls services when state changes.
- `contracts/` owns API request/response types and other shared service types.
- `lib/` owns pure reusable logic and utilities that are not service or state
  boundaries.

Route-private code follows the same boundaries inside the owning route folder:

- `_components/` contains components used only by that route subtree.
- `_hooks/` contains route-specific React hooks.
- `_lib/` contains route-specific pure helpers and presentation logic.
- `_services/` contains API/domain calls used only by that route subtree.
- `_types/` contains route-local contracts and types.
- `_constants/` contains route-local constants and presentation mappings.
- `_stores/` contains Zustand stores used only by that route subtree.

The underscore keeps implementation folders from becoming URL segments in a
future Next App Router build. Code used by more than one route subtree remains
in the shared top-level `components/`, `services/`, `contracts/`, `store/`, or
`lib/` boundary. `web/scripts/check-frontend-boundaries.mjs` enforces the
folder names and prevents imports of a route-private module from outside its
owning `app` subtree.

Services are ordinary importable TypeScript modules, not Angular-style
dependency-injected classes. Services must not update Zustand stores or import
React UI. A workflow that coordinates multiple services may return a result to
the store or page, but it must not hide store mutations inside the service.

The migration has two runtime stages:

1. Move and refactor the real page code under `src/app` while the current Vite
   + React Router runtime continues to work.
2. After the source tree is stable, perform the actual Next.js App Router
   cutover as a separate reviewed stage.

During stage 1, `web/src/app/router.tsx` is only the temporary React Router
route registry. It imports the actual page implementations from their new
locations; it is not an adapter around an old screen tree. `main.tsx` becomes
the Vite mount only and is removed/replaced at the Next cutover.

Do not create `web/src/app/pages/`. In Next App Router, `pages` would be a
literal URL segment. The route for `/login` is `app/login/page.tsx`, not
`app/pages/login.tsx`.

Testing is intentionally reset at the route-structure boundary. Delete the
current frontend tests rather than moving or adapting them. Do not add
replacement coverage in this effort; a separate follow-up session will
recreate the test strategy after the structure and runtime decision settle.

## Mission and constraints

Convert the current page-oriented frontend into a real route-owned `src/app`
tree without leaving the old page implementations behind. Preserve current
product behavior during the source migration, then make the same codebase
ready for a real Next App Router runtime.

The following remain fixed during stage 1:

- FastAPI continues to serve `/api/v1/*` and the built SPA from one origin.
- Vite and React Router remain the active browser runtime until the explicit
  Next cutover stage.
- The Python HTML renderer remains canonical for preview and PDF; React stays
  the schematic editing surface.
- API contracts, auth behavior, preview/PDF behavior, and template rendering
  are not intentionally changed during the source migration. The Builder URL
  is intentionally changed from `/dashboard/builder/:id` to `/builder/:id`.
- No broad API-service, shared-component, or domain-model rewrite is included.
- Backend tests remain outside this frontend restructuring scope. Frontend
  tests are deleted and rebuilt later as a separate effort.

## Verified repository baseline

The current routed screen files are under `web/src/features/<page>/`. These
directories are mostly page slices rather than reusable cross-route features.
The new structure will move page-owned code into `app/`; common API/domain
operations become importable modules under `services/`, global client state
moves to `store/`, and pure editor utilities remain under `lib/`. Shared visual
components remain under `components/` and shared domain component folders.

The original route tree was declared in
[`web/src/main.tsx`](../../web/src/main.tsx):

| URL | Current implementation | New implementation location |
|---|---|---|
| `/` | `features/home/HomePage.tsx` | `app/page.tsx` |
| `/login` | `features/login/LoginPage.tsx` | `app/login/page.tsx` |
| `/register` | `features/register/RegisterPage.tsx` | `app/register/page.tsx` |
| `/agent/tailor/:sessionId` | `features/agent-tailoring/AgentTailoringPage.tsx` | `app/agent/tailor/[sessionId]/page.tsx` |
| `/dashboard` | `features/dashboard/DashboardPage.tsx` | `app/dashboard/page.tsx` |
| `/dashboard/cvs` | `features/cv-list/CvListPage.tsx` | `app/dashboard/cvs/page.tsx` |
| `/dashboard/library` | `features/library/LibraryPage.tsx` | `app/dashboard/library/page.tsx` |
| `/dashboard/applications` | `features/applications/ApplicationsPage.tsx` | `app/dashboard/applications/page.tsx` |
| `/dashboard/applications/:id` | `features/application-detail/ApplicationDetailPage.tsx` | `app/dashboard/applications/[id]/page.tsx` |
| `/builder/:id` | `features/builder/BuilderPage.tsx` | `app/builder/[id]/page.tsx` |
| `/dashboard/settings` | `features/settings/SettingsPage.tsx` | `app/dashboard/settings/page.tsx` |
| `/*` | `features/not-found/NotFoundPage.tsx` | `app/not-found.tsx` |

Important coupling found during verification:

- Twenty-seven frontend files import `react-router-dom` across source and test
  files; twenty of those are production files. The concentration is in
  `main.tsx`, `App.tsx`, `AppLayout`, `ProtectedRoute`, `ErrorBoundary`,
  navigation-heavy screens, and the Builder.
- `AppLayout` mixes visual shell, links, location inspection, navigation, and
  logout behavior.
- `ProtectedRoute` mixes auth hydration with React Router redirects and
  location state.
- The Builder parses route state and uses `useBlocker` for unsaved changes,
  in addition to browser `beforeunload` handling. It should be migrated last.
- Auth hydration and several stores are browser-bound. A future server/client
  split cannot assume that the current local-storage lifecycle is SSR-safe.
- Existing API modules and Zustand stores already provide a useful boundary;
  move common API/domain modules to `services/` without replacing them with a
  second data layer.

Historical verification inventory from this checkout, not an acceptance gate:

- `npm run test -- --run`: 57 files passed, 355 tests passed before the test
  reset.
- `npm run build`: passed.
- `npm run codegen:check`: passed.
- `npm run lint`: 80 existing problems, consisting of 77 errors and 3
  warnings, primarily in shared section/editor code and Builder-related files.

The existing smoke command is deferred with the later testing reset. It
references missing `api/scripts/smoke_live.py`, while
`api/tests/test_smoke_live.py` still imports it. Backend pytest also did not
complete in the current local Python 3.14.7 environment. Do not repair these
items during the frontend source migration.

## Framework constraints

Next’s App Router supports `src/app`, nested route folders, `page.tsx`,
`layout.tsx`, `loading.tsx`, `error.tsx`, `not-found.tsx`, and dynamic segments
such as `[id]`. Implementation code can remain outside `app/`, but in this
plan the actual page implementations themselves move into the route folders.
See the [Next.js project structure
documentation](https://nextjs.org/docs/app/getting-started/project-structure).

Next pages and layouts are Server Components by default. Current pages use
state, effects, browser storage, forms, drag-and-drop, Lexical, iframe
preview, and client auth. During the eventual Next stage, mark those page
modules or their directly-owned components as client code where required; do
not claim that moving a file under `app/` makes it SSR-safe. See [Next Server
and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components).

React Router’s `useBlocker` exposes `proceed` and `reset` for in-app SPA
navigation but does not cover hard reloads or cross-origin navigation. Next’s
documented `Link` `onNavigate` callback can prevent a client-side link
navigation, but is not a complete equivalent for programmatic, back, and
forward navigation. Preserve the Builder’s current behavior during stage 1
and define the client-side Next behavior during stage 2. See [React Router
`useBlocker`](https://reactrouter.com/api/hooks/useBlocker) and [Next Link
navigation](https://nextjs.org/docs/app/api-reference/components/link).

## Target source tree

The intended source tree after the direct migration is:

```text
web/src/
  app/                              # actual route-owned implementations
    layout.tsx                      # root layout
    page.tsx                        # home implementation
    loading.tsx
    error.tsx
    not-found.tsx
    router.tsx                      # temporary React Router registry only
    _providers/
      ClientProviders.tsx
      AuthBoundary.tsx
    login/
      page.tsx                      # moved LoginPage implementation
      _components/                  # login-only components
    register/
      page.tsx
      _components/
    agent/tailor/[sessionId]/
      page.tsx
    dashboard/
      layout.tsx                    # moved dashboard shell/auth composition
      page.tsx
      _components/                  # dashboard-owned components
      _constants/
      _lib/
      _services/
      _stores/
      _types/
      cvs/
        page.tsx
        _components/
        _services/
        _types/
      library/
        page.tsx
        _components/
      applications/
        page.tsx
        _components/
        _lib/
        [id]/
          page.tsx
          _hooks/
          _lib/
          _services/
          _types/
      settings/page.tsx
    builder/
      [id]/
        page.tsx
        _components/
        _hooks/
        _lib/
        _services/
        _stores/
        _types/

  contracts/                       # API request/response and service types
    auth.ts
    applications.ts
    cvs.ts
    library.ts
    templates.ts

  services/                        # common frontend API/domain operations
    client.ts
    auth.ts
    cvs.ts
    applications.ts
    library.ts
    templates.ts

  store/                            # global client state
    authStore.ts
    cvStore.ts
    libraryStore.ts
    uiStore.ts

  components/                       # genuinely shared UI/domain components
  lib/                               # pure reusable logic and utilities
    llm/
    sections/
    security/
    validators/
```

Page-owned components move with their page. For example, login form code
belongs under `app/login/_components/`, while an application card used by both
the list and detail screens remains in a shared application component folder.
Use the import graph to decide; do not move code merely because it is nearby.

When a page migration is complete, its old
`web/src/features/<page>/` implementation and tests are removed. No old page
component is retained as an intermediate source of truth.

## Direct migration rules

### Route ownership

Every URL maps to one actual implementation file under `app/`. The file is
not a wrapper that re-exports an old screen. It owns the page composition,
route hooks needed by the current runtime, page-level data loading, and page
navigation.

The temporary `app/router.tsx` contains only the Vite/React Router registry.
It points at the actual `app` page modules and is deleted or replaced when
Next takes over. There must not be a second route tree under `features/` or a
parallel `routes/` directory.

### Root layout

Absorb `App.tsx` into `app/layout.tsx` rather than wrapping it from a new
adapter. The layout owns the root visual shell, providers, toasts, and the
current error boundary behavior. During Vite operation it renders the router
outlet; during the Next stage it accepts Next `children`.

Browser-only setup moves into `app/providers/ClientProviders.tsx`. The root
layout remains responsible for composition, not for inventing a new state or
API layer.

### Dashboard layout and auth

Rewrite `AppLayout` directly as `app/dashboard/layout.tsx`. Move its shell,
navigation, active-route behavior, builder layout behavior, and logout logic
into that route-owned implementation or directly shared components where
reuse is proven.

Rewrite `ProtectedRoute` directly as `app/providers/AuthBoundary.tsx` or a
dashboard-owned auth boundary. Preserve hydration and redirect behavior in
stage 1. During the Next stage, replace browser-only redirect mechanics with
the selected cookie/session and client-boundary design.

### Route data and navigation

Refactor each moved page in place:

- Route parameters become the page’s own route data (`id` or `sessionId`).
- Query values receive documented defaults.
- Internal navigation stays in the page or a genuinely shared navigation
  component, not in the old feature directory.
- API/domain calls use `services/`; Zustand stores use `store/`, and pure editor
  utilities remain in `lib/`.
- External links remain ordinary anchors.

While Vite/React Router is active, moved pages may use its hooks directly.
When the actual Next runtime is introduced, replace those hooks with Next page
`params`, `searchParams`, `Link`, and `useRouter` behavior in the same page
files or their directly-owned client components. This is a direct rewrite,
not a wrapper around the old implementation.

## Service, store, and contract boundaries

The service layer is the frontend application boundary around FastAPI. Each
service exposes named operations such as `fetchCV`, `updateProfile`, or
`listApplications`; it owns request paths, request payloads, response parsing,
and transport-specific behavior. It returns data or errors and does not know
about React components, Zustand stores, or toasts.

The store layer owns client state. Store actions call services, set loading and
error state, and commit returned data. A store may coordinate a workflow, but
the service must not call `useStore.getState()` or mutate another store.

The contracts layer contains API wire types and shared service types. Consumers
that need only a type use `import type` from `contracts/` without importing the
runtime API client. Generated schema types remain generated and are not copied
into the contracts layer.

Pure functions remain in `lib/`: section transforms, style/default logic,
validators, URL safety checks, and other environment-independent helpers. They
can be called by services, stores, or components without becoming services
themselves.

The dependency direction is:

```text
app/components → store → services → API client → FastAPI
       └──────────────→ contracts / pure lib helpers
```

The current `services/client.ts` is browser-bound because it uses cookies,
redirects, and the client toast integration. During the Next cutover, any
server-only service must be placed behind a server boundary and must not import
Zustand or browser-only services. Client services and server services must not
be mixed in one module.

## Bounded implementation sequence

Each step should be independently reviewable and committed separately. Do
not combine a source migration step with unrelated backend work. Frontend
tests are deleted during the source move and are not adapted between steps.

### 0. Freeze the route and ownership contract

- Record the route mapping above as the acceptance contract.
- Confirm current URL behavior, wildcard not-found behavior, dashboard nesting,
  auth redirects, and builder navigation behavior.
- Inventory each file under the twelve current page slices and mark it as
  page-owned, shared, or obsolete.
- Record the historical test/lint/build state without treating tests as a
  gate.
- Mark the stale smoke runner for the later testing session; do not repair it
  in this migration.

### 1. Create the real `src/app` tree and move page code

- Create the exact route folders and filenames in the target tree.
- Move each existing page implementation into its matching `app/**/page.tsx`
  location with `git mv` or an equivalent history-preserving change.
- Move page-owned components, styles, and helpers beside the page that owns
  them.
- Move root and dashboard composition into `app/layout.tsx` and
  `app/dashboard/layout.tsx` as part of the direct ownership change.
- Move the not-found implementation into `app/not-found.tsx`.
- Delete all current frontend test files instead of moving or adapting them.
- Remove empty/obsolete page-specific `features/<page>` directories. Retain a
  feature folder only when the import graph proves it is cross-route code.
- Move common frontend API/domain modules from `lib/api/` into `services/` and
  update consumers to import those canonical modules directly. Keep stores,
  validators, security helpers, and pure section utilities in their canonical
  `store/` and `lib/` boundaries.
- Add the `@/*` TypeScript/Vite alias needed by the new imports.

Acceptance: every current route has one real implementation under `app/`, no
page implementation remains under `features/`, and the source tree contains
no duplicate page authority.

### 2. Rebuild the current Vite runtime around the new files

- Create `app/router.tsx` with the existing React Router route map, importing
  the new page and layout modules directly.
- Reduce `main.tsx` to the Vite root mount and `RouterProvider` setup.
- Remove the old `App.tsx` route composition once `app/layout.tsx` owns it.
- Keep route URLs, nested dashboard layout behavior, auth redirects, and
  wildcard fallback unchanged, apart from the explicit Builder move to
  `/builder/:id`.
- Update imports throughout the moved code without introducing compatibility
  re-export files in the old locations.

Acceptance: Vite builds and the existing application can be navigated through
the new app-owned source tree. The router registry is the only temporary
React Router runtime file.

### 3. Complete the direct page refactors

Refactor the moved implementations in this order:

1. Home.
2. Login and register.
3. Agent tailoring (`sessionId`).
4. Dashboard home and dashboard shell.
5. CV list.
6. Library (`kind` query value).
7. Applications list.
8. Application detail (`id`).
9. Settings.
10. Builder (`id`, query values, unsaved state), last.

For each page:

- Remove imports that only existed because the file lived under `features/`.
- Keep page composition in the new `app` file.
- Move only genuinely shared code to shared folders.
- Preserve API/store behavior and visible UX.
- Do not create a re-export adapter in the old path.

The Builder gets a separate review before its move. Preserve `useBlocker`,
`beforeunload`, template-switch confirmation, preview iframe behavior, and
PDF export behavior during the Vite stage.

### 4. Separate services, stores, and contracts

- Move the global Zustand stores from `lib/store/` into the top-level `store/`
  directory and update consumers.
- Extract raw authentication requests, session loading, refresh, and logout
  operations from `authStore` into `services/auth.ts`. Leave state transitions,
  hydration status, and client state in `authStore`.
- Ensure the other stores call service operations rather than the HTTP client
  directly. Store actions remain responsible for loading, error, and cache
  updates.
- Move API request/response interfaces into the matching files under
  `contracts/` and import them with `import type`. Cover all current service
  domains, starting with `applications`, `cvs`, and `library`; do not duplicate
  types that already come from generated schema output.
- Remove service dependencies on Zustand stores, React components, and UI
  toasts. Handle user-facing notifications in stores or page-level client
  code.
- Keep browser-only services separate from any future server-only services.

Acceptance: service modules expose reusable operations and return data/errors;
stores own client state; contracts contain shared wire types; and the
dependency direction is one-way from stores to services.

### 5. Establish Next-compatible boundaries in the actual files

- Make `app/layout.tsx` a direct root layout implementation that can accept
  Next `children` at cutover.
- Make `app/dashboard/layout.tsx` the direct dashboard composition boundary.
- Add `app/providers/ClientProviders.tsx` and the direct auth boundary for
  browser-only behavior.
- Add `app/loading.tsx`, `app/error.tsx`, and `app/not-found.tsx` using the
  existing loading, error, and fallback presentation.
- Classify each moved page as client-only or potentially server-shell plus
  client content.
- Keep Builder, preview, rich text, forms, auth hydration, and browser storage
  client-only initially.

Acceptance: the app tree has the correct Next file conventions, and the
client/server boundary is documented per page without pretending stage 1 is
already SSR.

### 6. Perform the actual Next runtime conversion

After the direct source migration is accepted, install and configure Next in a
separate reviewed stage. This is a real runtime change, not a proof-of-concept
wrapper around Vite pages.

- Replace the Vite entrypoint and React Router runtime with Next App Router.
- Remove `app/router.tsx` and React Router dependencies from production code.
- Convert dynamic page files to Next `params` and `searchParams` contracts.
- Convert internal links to Next `Link` where appropriate.
- Use `useRouter` only inside client components that need imperative
  navigation.
- Apply `use client` directly to interactive page files/components where
  required by Next.
- Implement the selected auth/session model for server and client contexts.
- Define the Builder unsaved-navigation behavior for link, programmatic,
  back/forward, and hard-reload cases.

Do not remove Vite/FastAPI deployment code until the Next application is
usable and the deployment decision is accepted.

### 7. Complete deployment and cutover work

Decide whether the final system uses integrated single-origin hosting or a
separate Next frontend origin. Then update, as one separately reviewed
cutover:

- FastAPI static serving and SPA fallback behavior;
- Docker build and runtime configuration;
- `dev.sh` and local development commands;
- `README.md` and `DEPLOY.md`;
- API origin, cookies, CSRF, refresh, and unauthorized redirects;
- preview HTML and PDF endpoint access.

Remove obsolete Vite/React Router files only after manual route, auth,
preview, PDF, and deployment checks pass.

## Non-goals

- No thin route adapters or duplicate old page implementations.
- No `src/routes` tree.
- No `src/app/pages` tree.
- No test migration or replacement coverage during this effort.
- No rebuilding of the frontend/backend test suites until the separate testing
  session.
- No API contract, renderer, template, or PDF pipeline rewrite.
- No broad shared-component cleanup without import-graph evidence.
- No attempt to make Builder or every dashboard page server-rendered.
- No silent auth/session change; it requires an explicit design decision.

## Deferred testing reset

The current frontend test files are intentionally removed during the direct
source migration. A later session owns:

- recreating tests around the final `app` page/layout ownership;
- deciding unit, integration, and browser coverage for the new runtime;
- rebuilding Builder unsaved-navigation coverage;
- restoring or replacing `api/scripts/smoke_live.py` and its stale import;
- re-establishing backend/frontend smoke gates under supported environments.

Until that session is complete, the absence of frontend tests is expected and
must not be described as a passing test baseline.

## Verification and rollback

Use non-test checks during this effort:

- Run `npm run build` after each structural step.
- Run `npm run codegen:check` when generated schema imports are touched.
- Run focused ESLint on changed non-test files and record historical debt.
- Manually inspect every affected URL, including dynamic IDs, query values,
  auth redirects, dashboard nesting, and wildcard not-found.
- Manually confirm API requests, logout, preview iframe behavior, unsaved
  changes, and PDF export.
- For the Next stage, manually verify server/client rendering boundaries,
  cookies/CSRF, refresh, unauthorized redirects, and deployment topology.

Do not run or repair `./dev.sh --smoke` as part of this plan; the smoke gate
belongs to the deferred testing reset.

Keep each source-migration step in its own commit and use a separate
branch/worktree. A step must be revertible with one commit revert. Do not use
destructive resets or overwrite unrelated work.

Update the project tracker after each implementation step, then rebuild and
validate the graph.

## Estimate

Direct source migration under the current runtime: approximately **6–10
engineering days**.

Approximate allocation:

- route/ownership inventory: 0.5–1 day;
- direct app tree move and import cleanup: 2–3 days;
- root/dashboard/auth composition: 1–2 days;
- direct page refactors, with Builder last: 2–4 days;
- service/store/contract separation: 0.5–1 day;
- Next-compatible boundaries and manual verification: 1–2 days.

Actual Next runtime and deployment conversion: approximately **5–10 additional
engineering days**, with the largest risks in session auth, client/server
boundaries, Builder navigation blocking, and deployment topology.

The later testing reset is estimated separately and is intentionally not part
of these figures.

## Decisions to resolve before implementation

1. **Auth model:** choose the cookie/session contract that works in FastAPI
   and future Next Server/Client contexts.
2. **Next deployment:** choose integrated single-origin hosting or a separate
   Next frontend origin.
3. **Builder blocking:** define exact expected behavior for Next link,
   programmatic, back/forward, and hard-reload navigation.
4. **Testing reset timing:** start test recreation after the direct app tree is
   stable and the runtime decision is made.

The direct `src/app` ownership decision is settled by this plan. The remaining
questions concern auth, runtime cutover, deployment, and later testing.
