---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M27CJ5804VHXHGPM3R17JH5V
TYPE: bug
STATUS: DONE
PRIORITY: Medium
SEVERITY: Low
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS:
  files:
  - web/src/features/builder/BuilderPage.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-11T04:45:37.920128+00:00'
UPDATED_AT: '2026-09-11T04:45:37.920128+00:00'
---

# Return to application after editing application CV

## Background

Editing a CV from an application currently sends the builder Back action to the CV list instead of the originating application detail page.

## Investigation

The builder route already accepts an optional `application` query parameter,
and application detail links pass the originating application ID when opening
a linked CV. `BuilderPage` ignored that context and always wired its Back
button to `/cvs`.

## Decision

Use the existing route context rather than introducing browser-history
coupling. Return to `/applications/:id` when `applicationId` is present, and
retain `/cvs` for CVs opened from the CV list or other ordinary entry points.

## Implementation

Added a memoized `handleBack` callback in `BuilderPage` that selects the
application detail route when the optional application ID is present and the
CV list otherwise.

## Verification

`cd web && npm run typecheck`, `npm run lint`, `npm run architecture:test`, and
`npm run architecture:check` passed.

The full `./dev.sh --smoke` gate completed the backend ruff, frontend ESLint,
and production build stages, but its isolated Alembic migration exceeded the
30-second timeout in this environment before the live route checks.

## Follow-up
