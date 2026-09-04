---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: Medium
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS:
- frontend
- organization
- nextjs
- migration
RELATIONS: null
AFFECTS:
  files:
  - web/src/main.tsx
  - web/src/pages/
  - web/src/components/
  - web/src/features/
  - web/tsconfig.json
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T17:28:58.714814+00:00'
UPDATED_AT: '2026-09-04T17:28:58.714814+00:00'
---

# Page-oriented frontend ownership

## Background

The frontend currently has twelve routed page components under `web/src/pages/` and domain-oriented component folders under `web/src/components/`. The requested change is to make page ownership explicit without changing UI behavior, API contracts, routing URLs, or the HTML-first renderer.

## Investigation

The common-component assertion is mostly confirmed. `web/src/components/common/` already separates generic UI primitives (`Modal`, `EmptyState`, `LoadingSkeleton`, `AccordionPanel`, `Toast`) from application infrastructure (`AppLayout`, `ProtectedRoute`, `ErrorBoundary`). The CV-list components are already isolated in `web/src/components/cv-list/`, and direct page reuse is limited.

The important shared boundary is not generic common UI: the section editor/profile subsystem is consumed by Builder, Library, and Settings through `SectionEditorPanel`, `SectionRegistry`, profile components, and supporting controls. It must remain shared until its actual ownership is re-evaluated. `Modal`, `LoadingSkeleton`, and `EmptyState` also remain in place during the page slices.

The safest future Next.js shape is to keep page-owned code in `web/src/features/<page>/` and make route files thin adapters. This avoids growing arbitrary components inside a future Next `src/app/` route tree while allowing App Router `page.tsx` files to import the feature implementation later. The migration remains client-first because the builder, Zustand stores, React Hook Form, Lexical, iframe preview, and browser APIs require client components.

## Decision

Adopt a page-feature organization incrementally:

- Move one routed page and only its page-owned components/tests per step.
- Use `web/src/features/<page>/` for page-owned implementation and update only that route’s import wiring.
- Leave `web/src/components/common/` unchanged in the first pass; revisit only after all page slices are stable.
- Keep cross-page feature systems shared when the import graph proves reuse, especially the section editor/profile subsystem and generic UI primitives.
- Preserve React Router URLs and FastAPI static SPA deployment throughout this refactor.
- Treat each step as a reversible mechanical move with focused tests, lint, and production build checks.

This improves Next.js migration readiness by separating route-owned composition from reusable systems, but it does not itself require Next.js, SSR, or a renderer rewrite. A later Next migration can add thin App Router route files around these features.

## Implementation

Planned sequence (one page maximum per implementation step):

1. CV list — first low-risk slice; move `CvListPage`, CV-list components, and their tests.
2. Applications list — move list-only application composition; keep the form shared until proven page-specific.
3. Application detail — move detail composition and page tests.
4. Library — move library-page composition; keep shared editor/profile code shared.
5. Settings — move settings-only composition; keep shared profile/editor code shared.
6. Builder — move builder orchestration and builder-only composition; preserve shared editor, preview, and customization boundaries.
7. Dashboard — move dashboard-only composition while retaining `AppLayout` as shared infrastructure.
8. Home — move the public home page.
9. Login — move login page composition.
10. Register — move registration page composition and preserve Turnstile behavior.
11. Agent tailoring — move the session-based tailoring page.
12. Not found — move wildcard fallback composition.

After the page slices, perform a separate review of `components/common/` and shared feature folders. Add path aliases or Next route adapters only in a bounded foundation step if the import graph shows they reduce risk; do not combine that work with a page slice.

## Verification

Each page step must pass its focused tests, frontend lint, TypeScript/Vite production build, and `npm run codegen:check`. The full frontend suite and the existing live smoke gate should be run at milestone points. Verify the original worktree remains unchanged and the branch contains no route or behavior changes beyond ownership/import paths.

## Follow-up

Next.js viability remains conditional: the refactor makes ownership and future route entrypoints clearer, but it does not create SSR value by itself because the editor is highly client-side and the canonical preview/PDF path stays in FastAPI/Python. Reassess Next.js after page ownership stabilizes and a concrete need for SSR, route-level metadata, or Next-managed deployment exists.
