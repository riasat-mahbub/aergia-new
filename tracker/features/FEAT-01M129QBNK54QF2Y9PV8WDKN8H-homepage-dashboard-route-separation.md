---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN8H
TYPE: feature
STATUS: DONE
SUMMARY: Public home page at /, protected dashboard at /dashboard
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- routing
- ui
- phase-11
RELATIONS:
  related:
  - BUG-01M129QBNK54QF2Y9PV8WDKN72
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:11:58.124148+00:00'
UPDATED_AT: '2026-08-01T16:11:58.124148+00:00'
---

# HomePage + dashboard route separation

## Background

Public home page at /, protected dashboard at /dashboard

Route structure:
- `/` → public HomePage with marketing layout and login/register buttons
- `/dashboard` → protected CvListPage
- `/dashboard/builder/:id` → protected builder
- `/dashboard/settings` → protected settings page
- Hydrated guard in ProtectedRoute to prevent redirect flash

HomePage features emerald theme, feature grid, and conditional CTAs
(login/register when logged out, "My CVs" when logged in).

*Migrated from SCHEMA 2 entry 017-dashboard-routes.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification

All Phase 11 tasks complete.

## Follow-up

<!-- Migrated from FEAT-01KYZ1HD9CXS24FQ19PBX1T219 during the schema-4 cutover. -->
