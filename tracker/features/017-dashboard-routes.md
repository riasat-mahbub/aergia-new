---
ID:             017
TYPE:           feature
NAME:           HomePage + dashboard route separation
SUMMARY:        Public home page at /, protected dashboard at /dashboard
STATUS:         CLOSED
TAGS:           routing, ui, phase-11
LINKS:          phase=COMPLETED.md-phase-11
---

## Description

Route structure:
- `/` → public HomePage with marketing layout and login/register buttons
- `/dashboard` → protected CvListPage
- `/dashboard/builder/:id` → protected builder
- `/dashboard/settings` → protected settings page
- Hydrated guard in ProtectedRoute to prevent redirect flash

HomePage features emerald theme, feature grid, and conditional CTAs
(login/register when logged out, "My CVs" when logged in).

## Status

All Phase 11 tasks complete.
