---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KYZ1D257KRJHAB9XDQ7RC79X
TYPE: bug
STATUS: DONE
SUMMARY: 'After restructuring routes to /dashboard/*, old hardcoded paths caused 404s'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- routing
- '404'
- navigation
- phase-11
RELATIONS:
  related:
  - FEAT-01KYZ1HD9CXS24FQ19PBX1T219
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:09:35.655795+00:00'
UPDATED_AT: '2026-08-01T16:09:35.655795+00:00'
---

# Route 404s after URL structure overhaul

## Background

After restructuring routes to /dashboard/*, old hardcoded paths caused 404s

When the route structure was changed from `/builder/:id` and `/` (CvList)
to `/dashboard/builder/:id` and `/` (HomePage) + `/dashboard` (CvList),
multiple components had hardcoded old paths:

1. CvListPage navigated to `/builder/:id` (404)
2. CreateCvModal navigated to `/builder/:id` (404)
3. LoginForm hardcoded redirect (ignored location state)
4. BuilderPage back button navigated to `/` instead of `/dashboard`
5. AppLayout links pointed to wrong paths
6. NotFoundPage and ErrorBoundary had wrong "go to dashboard" links

*Migrated from SCHEMA 2 entry 006-route-404s.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation

Swept through all pages and components to fix navigation paths. 10 files
were modified in a single phase.

### Phase
Phase 11 Bugfix — Route Cleanup

## Verification


## Follow-up
