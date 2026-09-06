---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1T4CK4XBBETG797XE09F3SG
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS:
- architecture
- frontend
RELATIONS:
  related:
  - TASK-01M1T3PYBVW4Y7QCQTB6SPG22G
  - FEAT-01M1T1HE13NNW3KBFWBAMV79VQ
AFFECTS:
  files:
  - web/src/app-shell/ClientProviders.tsx
  - web/src/app-shell/ErrorPage.tsx
  - web/src/app-shell/LoadingPage.tsx
  - web/src/app-shell/NotFoundPage.tsx
  - web/src/app-shell/RootLayout.tsx
  - web/src/app-shell/WorkspaceLayout.tsx
  - web/src/app-shell/components/SiteNavbar.tsx
  - web/src/app-shell/index.ts
  - web/src/routes/__root.tsx
  - web/src/routes/_authenticated/_workspace/route.tsx
  - web/src/routes/_authenticated/builder/route.tsx
  - web/src/features/dashboard/index.ts
  - web/src/features/home/HomePage.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-06T01:12:39.325133+00:00'
UPDATED_AT: '2026-09-06T01:12:39.325133+00:00'
---

# Move application shell to src/app-shell

## Background

Move global application layout, providers, navigation, and fallback UI out of features/app-shell into src/app-shell; rename DashboardLayout to WorkspaceLayout.

## Investigation

The shell was stored under `features/app-shell`, even though it owns global
providers, navigation, root layout, and fallback UI. `DashboardLayout` was
also a shared authenticated workspace shell used by both workspace routes and
the builder.

## Decision

Keep product capabilities under `features/` and move the global shell to
`src/app-shell/`. Rename `DashboardLayout` to `WorkspaceLayout` so its role is
not tied to the Dashboard page. Keep the builder's explicit navbar opt-out.

## Implementation

Moved the app-shell module to `src/app-shell`, updated its public entrypoint,
moved and renamed the layout, and updated root, home, workspace, and builder
imports. No test files were added or deleted.

## Verification

Build, typecheck, lint, architecture fixtures/checks, codegen check, and diff
check passed. Lint has only the existing hook warnings. The smoke gate reached
the live stage but stopped because the existing Alembic migration exceeded its
30-second timeout before servers started.

## Follow-up

Applications list/detail route cleanup remains separate work.
