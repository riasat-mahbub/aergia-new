---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M1PVF6YHVYYJMRQ52HQ4A13P
TYPE: feature
STATUS: PLANNED
PRIORITY: Medium
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS:
- frontend
- nextjs
- migration
RELATIONS:
  depends_on:
  - FEAT-01M1PT8A0VE6WB4TC3Q7PZWF1H
AFFECTS:
  files:
  - web/src/main.tsx
  - web/src/App.tsx
  - web/src/components/common/AppLayout.tsx
  - web/src/components/common/ProtectedRoute.tsx
  - web/src/components/common/ErrorBoundary.tsx
  - web/src/features/
  - web/src/lib/
  - web/tsconfig.json
  - web/vite.config.ts
  - web/package.json
  - README.md
  - DEPLOY.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T18:39:04.657087+00:00'
UPDATED_AT: '2026-09-04T18:39:04.657087+00:00'
---

# Next.js readiness foundation

## Background

Prepare the existing Vite/React Router frontend for a later Next.js App Router migration without switching frameworks now: separate route adapters from screen implementations, extract router-coupled layouts and navigation, document client boundaries, add route-friendly aliases, and preserve FastAPI SPA deployment until cutover.

## Investigation

The current runtime is still Vite plus React Router: `web/src/main.tsx` owns
the complete route tree, while `App`, `AppLayout`, `ProtectedRoute`, and
`ErrorBoundary` combine application composition with router APIs. Twenty-seven
frontend files import `react-router-dom` when tests are included. The page
surfaces also use Zustand, effects, browser APIs, form libraries, and the
iframe preview, so they will remain client-heavy during an eventual Next.js
adoption. Typed API wrappers and Zustand stores are already separated from UI
under `web/src/lib/`.

The current `web/src/features/<page>/` directories are mostly screen/page
slices rather than true cross-route features. The readiness work should not
expand that naming conflation: route ownership belongs in the route layer,
while cross-page capabilities belong in feature modules.

## Decision

Use a route-adapter layer as the next incremental seam. During the Vite phase,
keep the current router and use a neutral `web/src/routes/` convention rather
than creating a decorative Next `app/` directory that has no runtime meaning.
At the actual framework cutover, those adapters can become thin Next App
Router `page.tsx`/`layout.tsx` files. Keep page implementation and true
cross-page capabilities outside the route layer.

Do not make the Builder or preview server-rendered as part of the readiness
work. First isolate router and browser concerns, then classify each route as a
server shell plus client surface or an entirely client route.

## Implementation

- Add a route map/adapter convention and a Next-compatible `@/*` import alias
  in TypeScript and Vite without changing route URLs.
- Split router-independent visual shells from router bindings: root providers,
  dashboard layout/navigation, auth guard, error boundary, links, and route
  parameter extraction.
- Move `useParams`, `useLocation`, `useNavigate`, `useSearchParams`, and
  `useBlocker` toward route adapters or a small navigation boundary; keep page
  components callable with explicit route data where practical.
- Establish loading, error, and not-found conventions that map to Next's
  `loading.tsx`, `error.tsx`, and `not-found.tsx` later.
- Keep the FastAPI single-origin/static-SPA deployment and Axios/Zustand
  behavior unchanged until a separate Next runtime proof-of-concept succeeds.
- Migrate one route adapter at a time, with the dashboard layout treated as a
  separate bounded step from any individual page.

Suggested route sequence: root/auth, agent tailoring, dashboard shell/auth,
dashboard home, CVs, library, applications list, application detail, builder,
settings, then wildcard not-found.

## Verification

Each step should run the affected Vitest tests, TypeScript/Vite production
build, codegen drift check, and route smoke coverage. Milestones should also
run the full frontend suite and `./dev.sh --smoke`. A step is complete only if
React Router URLs and FastAPI SPA serving remain unchanged.

Readiness estimate: roughly 8–14 engineering days, depending on how much
router coupling is removed from the Builder and shared layout. A real Next.js
runtime/deployment cutover remains a separate roughly 5–10 day effort, with
additional risk around auth, static serving, and client/server boundaries.

## Follow-up

Reassess whether Next.js provides enough value after the route-adapter and
client-boundary work. The first proof-of-concept should target a low-risk
public/auth route, not the Builder.
