# Handoff: plan the Next.js-readiness foundation

**Date:** 2026-09-04
**Audience:** The next planning/implementation agent
**Status:** Planning handoff only; do not begin code changes until the implementation plan is reviewed.

## Mission

Design a safe, incremental set of changes that makes the frontend structurally
closer to a Next.js App Router application without switching from Vite,
React Router, or FastAPI yet.

The plan should separate route ownership from screen implementation, isolate
browser/router concerns, and create seams that can later become Next
`page.tsx`/`layout.tsx` files. It must preserve the current product while
preparing for a later framework decision.

## Current repository state

Aergia is a single-user CV builder with:

- FastAPI serving `/api/v1/*` and the built React SPA from one origin.
- React 19, Vite 6, TypeScript, Tailwind, Zustand, React Hook Form, Lexical,
  Motion, and React Router 7.
- An HTML-first Python renderer that produces both preview HTML and PDF; the
  React tree is the editing surface and is not the canonical renderer.
- A page-ownership refactor already merged into `master` at merge commit
  `16fcf2f`.

The refactor moved the twelve routed screens into
`web/src/features/<page>/`:

```text
agent-tailoring
application-detail
applications
builder
cv-list
dashboard
home
library
login
not-found
register
settings
```

Important terminology correction: these directories are mostly page/screen
slices, not true cross-route features. Do not expand the naming conflation.
True shared/domain code remains in:

```text
web/src/components/common/       # generic UI and app infrastructure
web/src/components/sections/     # shared section editors and rich text
web/src/components/profile/      # shared profile UI
web/src/components/library/      # shared library UI
web/src/components/applications/ # shared application form/presentation
web/src/lib/api/                 # typed HTTP wrappers
web/src/lib/store/               # Zustand state
web/src/lib/sections/            # shared section/domain helpers
```

The existing page refactor was intentionally mechanical. It did not change
route URLs, API contracts, auth behavior, or deployment.

## Current route tree

The single routing source is [`web/src/main.tsx`](../../web/src/main.tsx):

```text
/                              home
/login                         login
/register                      registration
/agent/tailor/:sessionId       agent tailoring landing page
/dashboard                    protected dashboard home
/dashboard/cvs                CV list
/dashboard/library            library
/dashboard/applications       applications list
/dashboard/applications/:id   application detail
/dashboard/builder/:id        CV builder
/dashboard/settings           settings
/*                             not found
```

`/dashboard` currently nests `ProtectedRoute`, `AppLayout`, and an `Outlet`.
`App.tsx` wraps the router outlet with the toast container and error boundary.

## Evidence that matters for the plan

- Twenty-seven frontend files import `react-router-dom` when tests are
  included. The functional coupling is concentrated in page screens,
  `AppLayout`, `ProtectedRoute`, `ErrorBoundary`, and navigation-heavy
  components.
- `AppLayout` combines visual layout with `Link`, `NavLink`, `useNavigate`,
  `useLocation`, and logout behavior.
- `ProtectedRoute` combines auth hydration, `Navigate`, and router location
  state.
- Screens use Zustand, effects, browser APIs, form libraries, and the iframe
  preview. The Builder and preview should remain client-first in the initial
  readiness work.
- Existing API wrappers and stores already provide a useful non-UI boundary;
  a broad API-to-service rename is not part of this work.
- The full frontend baseline currently passes 57 test files / 355 tests,
  production build passes, and schema codegen check passes.
- Full frontend lint has existing debt: 77 `any` errors and 3 hook warnings,
  concentrated in shared section/editor code, Builder, and support code. Do
  not widen this effort into unrelated lint cleanup.

## Recommended target shape

During the remaining Vite phase, use a neutral route-adapter layer. Do not
create a decorative `src/app/` directory whose Next conventions are not
actually interpreted by the current runtime.

```text
web/src/
  routes/                       # React Router bindings for now
    root.tsx
    login.tsx
    register.tsx
    agent-tailor.tsx
    dashboard/
      layout.tsx
      index.tsx
      cvs.tsx
      library.tsx
      applications.tsx
      application-detail.tsx
      builder.tsx
      settings.tsx
    not-found.tsx

  features/                     # retain only where code is truly cross-page
    applications/
    authentication/
    cv-editor/
    library/

  components/                   # shared UI
  lib/                          # API, stores, pure domain utilities
```

At the actual Next cutover, the route adapters can become the corresponding
App Router files:

```text
web/src/app/
  layout.tsx
  page.tsx
  login/page.tsx
  register/page.tsx
  agent/tailor/[sessionId]/page.tsx
  dashboard/layout.tsx
  dashboard/page.tsx
  dashboard/cvs/page.tsx
  dashboard/library/page.tsx
  dashboard/applications/page.tsx
  dashboard/applications/[id]/page.tsx
  dashboard/builder/[id]/page.tsx
  dashboard/settings/page.tsx
  not-found.tsx
```

The route files should stay thin. Next's App Router uses filesystem
conventions for `page`, `layout`, loading, error, and not-found files; the
implementation does not need to live entirely under `app/`.

## Proposed bounded work sequence

The next agent should refine this into implementation tickets. Keep one route
or one foundation concern per step; never combine a route migration with a
framework/deployment cutover.

### 1. Foundation and naming

- Decide whether the interim adapter directory is `routes/` or another neutral
  name.
- Add a `@/*` TypeScript/Vite alias matching the likely Next import style.
- Decide whether current page slices remain under `features/` temporarily or
  are renamed to `screens/`/`pages/` as a separate mechanical cleanup.
- Do not add Next dependencies yet.

### 2. Root composition

- Split the router-independent root shell from `App.tsx`.
- Isolate toast/provider setup and error presentation so a future Next root
  `layout.tsx` can wrap a client provider component.
- Preserve the current React Router outlet during this step.

### 3. Dashboard layout and auth boundary

- Split the visual dashboard shell from router bindings in `AppLayout`.
- Split auth hydration/policy from React Router redirects in `ProtectedRoute`.
- Define how the current protected dashboard maps to a future
  `dashboard/layout.tsx`.
- Coordinate with the planned authentication lifecycle hardening work; do not
  assume that browser-local token state can support server rendering.

### 4. Navigation and route-data boundary

- Move `useParams`, `useLocation`, `useNavigate`, `useSearchParams`, and
  `useBlocker` toward route adapters or a deliberately small navigation
  boundary.
- Pass route IDs, session IDs, query values, and navigation callbacks into
  screen implementations where practical.
- Treat Builder's unsaved-change blocker as its own design decision; Next has
  no direct equivalent to the current React Router blocker behavior.
- Replace direct router imports in screen-owned components only one route at a
  time, preserving tests.

### 5. Client-boundary inventory

- Classify each route as an interactive client route or a possible server shell
  plus client surface.
- Keep Builder, preview, rich text, forms, auth hydration, and browser-storage
  behavior client-side initially.
- Identify low-risk public/auth content that could later demonstrate a server
  page without forcing the dashboard or Builder into SSR.

### 6. Loading, error, and not-found conventions

- Establish reusable loading and error presentation independent of the
  current router.
- Make the wildcard not-found screen map cleanly to a future Next
  `not-found.tsx`.
- Preserve the current fallback behavior and navigation links.

### 7. Route adapters, one at a time

Suggested order:

1. Home or login (choose the lower-risk proof route after inspection).
2. Register.
3. Agent tailoring.
4. Dashboard layout/auth boundary as a separate non-page step.
5. Dashboard home.
6. CV list.
7. Library.
8. Applications list.
9. Application detail.
10. Settings.
11. Builder last among dashboard routes.
12. Not found.

Each route step should change only its adapter/import boundary and the minimum
required screen props. Do not change URLs or API endpoints.

### 8. Next proof of concept

Only after the adapter and client-boundary work, create a disposable or
isolated Next proof of concept for a public/auth route. The agent must answer:

- How FastAPI remains the API and HTML/PDF renderer.
- Whether Next is deployed as a separate frontend origin or integrated behind
  the existing single origin.
- How auth/session state works in server and client contexts.
- Whether the expected SSR, metadata, or deployment benefit justifies the
  runtime change.

Do not use the Builder as the first proof route.

## Non-goals

- No immediate Next.js install or package-script replacement.
- No SSR conversion of all routes.
- No rewrite of the Python renderer or PDF pipeline.
- No API contract or backend route changes.
- No broad service-layer rename.
- No generic common-component cleanup unless the import graph proves a direct
  need.
- No replacement of React Router until the Next proof of concept is accepted.
- No changes to FastAPI static SPA serving during readiness work.

## Verification and rollback requirements

For every implementation step:

- Run the affected Vitest tests.
- Run `npm run build`.
- Run the codegen drift check.
- Run focused lint for changed files; record unrelated baseline failures.
- At milestones, run the full frontend suite and `./dev.sh --smoke`.
- Confirm route URLs, API requests, auth behavior, and preview/PDF behavior are
  unchanged.
- Keep each step in its own commit and use a separate branch/worktree.
- Update the project tracker before and after each step; rebuild and validate
  the graph.

Rollback for a route step should be a single commit revert. Do not use
destructive resets or overwrite unrelated work.

## Estimate

Planning/implementation estimate for the readiness foundation: **8–14
engineering days**.

Approximate allocation:

- Foundation/aliases: 0.5–1 day.
- Root and dashboard shell/auth separation: 2–4 days.
- Navigation and route-data isolation: 3–5 days.
- Client-boundary and loading/error conventions: 1.5–3 days.
- Next proof of concept and deployment decision: 1–2 days.

An actual Next.js runtime/deployment cutover is separate: approximately **5–10
additional engineering days**, with the largest risks in auth/session design,
React Router replacement, browser-only Builder behavior, and deployment
topology.

## Questions the next agent must resolve

1. Is `routes/` the best interim name, or should the project move directly to
   a real Next `app/` runtime when route adapters begin?
2. Should the current page slices be renamed to `screens/` before adding true
   feature modules?
3. What authentication/session model is acceptable for a future server/client
   split?
4. Which public/auth route offers the lowest-risk Next proof of concept?
5. Does the product have a concrete need for SSR, metadata, or Next-managed
   deployment, or is the readiness work primarily organizational?

## Related project records

- [Completed page ownership refactor](../../tracker/features/FEAT-01M1PT8A0VE6WB4TC3Q7PZWF1H-feat-01m1pqtq1tmrzxzs0zpyfrnnz5.md)
- [Next.js readiness foundation tracker item](../../tracker/features/FEAT-01M1PVF6YHVYYJMRQ52HQ4A13P-next-js-readiness-foundation.md)
- [Authentication lifecycle hardening](../../tracker/features/FEAT-01M17YJ3500AF0MCDSB6NKE9GT-authentication-lifecycle-hardening.md)
- [Next.js App Router project structure](https://nextjs.org/docs/app/getting-started/project-structure)
- [Next.js Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
