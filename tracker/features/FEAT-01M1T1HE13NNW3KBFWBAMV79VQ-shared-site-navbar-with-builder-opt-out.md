---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M1T1HE13NNW3KBFWBAMV79VQ
TYPE: feature
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS:
- ui
- navigation
- refactor
RELATIONS: null
AFFECTS:
  files:
  - web/src/features/app-shell/components/SiteNavbar.tsx
  - web/src/features/app-shell/index.ts
  - web/src/features/dashboard/DashboardLayout.tsx
  - web/src/features/home/HomePage.tsx
  - web/src/routes/_authenticated/builder/route.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-06T00:22:52.195380+00:00'
UPDATED_AT: '2026-09-06T00:22:52.195380+00:00'
---

# Shared site navbar with builder opt-out

## Background

Replace the duplicated HomePage and DashboardLayout headers with one SiteNavbar. The builder route explicitly hides the site navbar and keeps BuilderHeader as the sole top-level editor header.

## Investigation

HomePage and DashboardLayout had separate header implementations. DashboardLayout
also inferred builder mode from the URL and rendered a different top bar, which
stacked above BuilderHeader. The builder's existing unsaved-change blocker is
route-based and does not require global logout or navigation controls inside the
builder.

## Decision

Use one auth-aware SiteNavbar for the public home page and normal authenticated
pages. Its brand always links to `/`; authenticated users get the application
navigation and logout, while anonymous users get only Sign in. The builder route
explicitly opts out so BuilderHeader remains the only editor header.

## Implementation

Added SiteNavbar under the app-shell feature, moved the authenticated navigation
and logout flow into it, removed the duplicate HomePage and DashboardLayout
headers, and replaced pathname-based builder detection with
`showNavbar={false}` at the builder route layout.

## Verification

Frontend lint, typecheck, architecture fixtures, architecture checks, and the
production frontend build passed. The full smoke command reached the live smoke
stage but stopped because its isolated Alembic migration exceeded the 30-second
timeout before the live servers started.

## Follow-up
