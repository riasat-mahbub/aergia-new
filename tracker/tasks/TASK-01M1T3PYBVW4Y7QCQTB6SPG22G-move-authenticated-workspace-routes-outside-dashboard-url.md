---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1T3PYBVW4Y7QCQTB6SPG22G
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- routing
- navigation
RELATIONS:
  related:
  - FEAT-01M1T1HE13NNW3KBFWBAMV79VQ
  - FEAT-01M129QBNK54QF2Y9PV8WDKN8H
AFFECTS:
  files:
  - web/src/routes/_authenticated/_workspace/route.tsx
  - web/src/routes/_authenticated/_workspace/dashboard.tsx
  - web/src/routes/_authenticated/_workspace/cvs.tsx
  - web/src/routes/_authenticated/_workspace/library.tsx
  - web/src/routes/_authenticated/_workspace/settings.tsx
  - web/src/routes/_authenticated/_workspace/applications/route.tsx
  - web/src/routes/_authenticated/_workspace/applications/$id.tsx
  - web/src/features/app-shell/components/SiteNavbar.tsx
  - web/src/features/dashboard/pages/DashboardPage.tsx
  - web/src/features/dashboard/components/SummaryCard.tsx
  - web/src/features/dashboard/components/ApplicationRow.tsx
  - web/src/features/applications/components/ApplicationCard.tsx
  - web/src/features/applications/pages/ApplicationListPage.tsx
  - web/src/features/applications/pages/ApplicationDetailPage.tsx
  - web/src/features/builder/BuilderPage.tsx
  - web/src/features/builder/components/library/LibraryPicker.tsx
  - web/src/features/cvs/components/CvCard.tsx
  - web/src/features/library/pages/LibraryPage.tsx
  - web/src/features/tailoring/pages/TailoringSessionPage.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-06T01:00:49.915376+00:00'
UPDATED_AT: '2026-09-06T01:00:49.915376+00:00'
---

# Move authenticated workspace routes outside dashboard URL

## Background

Move authenticated CV, Library, Applications, and Settings pages from /dashboard/* to top-level workspace URLs while preserving the existing shared shell.

## Investigation

The dashboard route provided the shared navbar layout, while Dashboard, CVs,
Library, Applications, and Settings were already peer destinations in the
navbar. The builder already uses the same layout with the navbar disabled.

## Decision

Use a pathless `_workspace` route under the authenticated route. It keeps the
existing shell for normal workspace pages without adding `_workspace` to public
URLs. Remove the `/dashboard/*` child routes completely; do not add redirects.
Keep the shell ownership and deeper Applications route cleanup for a later
change.

## Implementation

Moved the authenticated page routes to `/dashboard`, `/cvs`, `/library`,
`/applications`, `/applications/$id`, and `/settings`. Updated navigation and
feature links, then regenerated the TanStack route tree.

## Verification

Frontend build, typecheck, lint, architecture tests/checks, codegen check, and
diff checks passed. The smoke gate reached its live stage but stopped because
the existing isolated Alembic migration exceeded its 30-second timeout before
servers started.

## Follow-up

Later move the shared layout from the Dashboard feature into app-shell and
clean up the Applications list/detail layout if needed.
