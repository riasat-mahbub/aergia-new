---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2V3CBCB2D31TK0TT98F21BW
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M2V32FH6J28MS7ESJB9CF4VY
AFFECTS:
  files:
  - web/src/features/home/HomePage.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-18T20:29:59.051255+00:00'
UPDATED_AT: '2026-09-18T20:29:59.051255+00:00'
---

# FEAT-01M2V32FH6J28MS7ESJB9CF4VY

## Background

Replaced the home navbar's rmahbub.com item with an auth-aware route link: signed-out visitors see Log in / Register linking to /login, while authenticated users see Dashboard linking to /dashboard. Footer attribution remains unchanged.

## Investigation

The home navbar previously used its final slot for the personal-site link,
while the primary action lived only in the hero and final call to action. That
made authentication navigation less discoverable.

## Decision

Use the existing auth store as the single branch condition. Keep the personal
site attribution in the footer, and use the navbar slot for the most relevant
next route: login/register for visitors and dashboard for authenticated users.

## Implementation

Replaced the header rmahbub.com anchor with a TanStack Router Link that renders
Log in / Register to /login when signed out and Dashboard to /dashboard when
authenticated.

## Verification

Passed lint and TypeScript checks. Headless browser verification confirmed the
signed-out label and /login href, with no console errors or horizontal
overflow; the authenticated branch uses the existing isAuthenticated state.

## Follow-up
