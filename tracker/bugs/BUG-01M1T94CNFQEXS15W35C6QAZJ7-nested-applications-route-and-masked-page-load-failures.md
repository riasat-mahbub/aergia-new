---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M1T94CNFQEXS15W35C6QAZJ7
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: Medium
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- routing
- loading
- frontend
RELATIONS:
  related:
  - TASK-01M1T3PYBVW4Y7QCQTB6SPG22G
AFFECTS:
  files:
  - web/src/routes/_authenticated/_workspace/applications/route.tsx
  - web/src/routes/_authenticated/_workspace/applications/index.tsx
  - web/src/routes/_authenticated/_workspace/applications/$id.tsx
  - web/src/routes/_authenticated/builder/index.tsx
  - web/src/routeTree.gen.ts
  - web/src/features/applications/pages/ApplicationListPage.tsx
  - web/src/features/applications/pages/ApplicationDetailPage.tsx
  - web/src/features/applications/state/applicationStore.ts
  - web/src/features/dashboard/components/SummaryCard.tsx
  - web/src/features/dashboard/pages/DashboardPage.tsx
  - web/src/features/cvs/pages/CvListPage.tsx
  - web/src/features/cvs/state/cvListStore.ts
  - web/src/features/library/components/LibraryProfileCard.tsx
  - web/src/features/library/pages/LibraryPage.tsx
  - web/src/features/library/state/libraryStore.ts
  - web/src/features/profile/state/profileStore.ts
  - web/src/features/settings/components/SettingsProfileCard.tsx
  - web/src/features/settings/pages/SettingsPage.tsx
  - web/src/features/builder/BuilderPage.tsx
  - web/src/features/builder/hooks/useBuilderDocumentLoader.ts
  - web/src/features/builder/state/builderDocumentStore.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-06T02:35:33.423366+00:00'
UPDATED_AT: '2026-09-06T02:35:33.423366+00:00'
---

# Nested applications route and masked page-load failures

## Background

The Applications route rendered its list component as a parent while also owning a nested detail route, so application detail pages were hidden because the parent had no Outlet. Several authenticated data stores also swallowed load failures and rendered empty or not-found states. Fixed the route hierarchy, added a /builder redirect, and added retryable load-error states.

## Investigation

The Applications directory route had a `$id.tsx` child but rendered the list
page itself instead of a layout with an outlet. The generated route tree
confirmed that `/applications/$id` was nested under that parent. The builder
route had a layout and dynamic child but no index route, so `/builder` could
render an empty shell. Applications, CV, Library, Profile, and Builder data
stores all converted load failures into empty or not-found UI states.

## Decision

Use an explicit Applications layout plus an index route. Redirect the bare
`/builder` path to `/cvs`, the existing entry point for selecting a document.
Keep data failures in store state and give affected pages a retry action while
preserving successful empty-state behavior.

## Implementation

Added the Applications outlet/index split and builder redirect, regenerated the
TanStack route tree, and added retryable error states to the affected stores and
pages. Builder document retry re-runs the document loader so its local draft
state is rebuilt as well.

## Verification

Frontend build and typecheck passed. Lint passed with the ten existing hook
dependency warnings. Architecture fixtures/checks, codegen check, and diff
check passed.

## Follow-up

The full live smoke gate was not rerun because its known isolated Alembic
migration timeout prevents the application servers from starting.
