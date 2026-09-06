---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1T80X17SVD08MVM44KM6NSE
TYPE: task
STATUS: DONE
PRIORITY: Low
SEVERITY: null
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS:
- architecture
- frontend
RELATIONS:
  related:
  - TASK-01M1T4CK4XBBETG797XE09F3SG
AFFECTS:
  files:
  - web/src/app-shell/layouts/RootLayout.tsx
  - web/src/app-shell/layouts/WorkspaceLayout.tsx
  - web/src/app-shell/providers/ClientProviders.tsx
  - web/src/app-shell/fallbacks/ErrorPage.tsx
  - web/src/app-shell/fallbacks/LoadingPage.tsx
  - web/src/app-shell/fallbacks/NotFoundPage.tsx
  - web/src/app-shell/index.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-06T02:16:10.535474+00:00'
UPDATED_AT: '2026-09-06T02:16:10.535474+00:00'
---

# Organize app-shell layouts and support files

## Background

Group app-shell layouts, providers, and fallback screens into dedicated subdirectories without changing behavior.

## Investigation

The app shell had layouts, providers, fallback screens, and navigation in one
directory. The shell is small but contains different responsibilities that are
clearer when grouped by role.

## Decision

Keep the public `app-shell` entrypoint, and organize its internals into
`layouts`, `providers`, `fallbacks`, and `components` directories.

## Implementation

Moved `RootLayout` and `WorkspaceLayout` into `layouts`, `ClientProviders`
into `providers`, and the error/loading/not-found screens into `fallbacks`.
Updated the barrel exports and relative imports. Behavior and routes are
unchanged.

## Verification

Build, typecheck, lint, architecture fixtures/checks, codegen check, and diff
check passed. Lint has only the existing hook warnings.

## Follow-up
