---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M129QBNK54QF2Y9PV8WDKN73
TYPE: bug
STATUS: DONE
SUMMARY: Early return guard before hooks prevents loadCV() from ever executing
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- builder
- react
- hooks
- loading
- early-return
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:09:35.729823+00:00'
UPDATED_AT: '2026-08-01T16:09:35.729823+00:00'
---

# BuilderPage "CV not found" stuck state

## Background

Early return guard before hooks prevents loadCV() from ever executing

The early return guard in BuilderPage.tsx was placed before all hook calls
(useState, useEffect). In React, hooks must run unconditionally on every
render. The guard prevented:

1. `useState` calls below the guard from being initialized
2. `useEffect` from being scheduled — this is where `loadCV(id)` lives

Flow: Component mounts with `isLoading=false`, `currentCV=null` →
Guard condition `isLoading || !currentCV` is true → returns early →
`useEffect` never runs → `loadCV()` never called → no API request →
Store state never changes → stuck on "CV not found" forever.

*Migrated from SCHEMA 2 entry 007-builder-cv-not-found.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation

Removed the early return guard before hooks. Added a `showLoading` state
initialized to `true`. Set it to `false` after `loadCV()` completes.
Moved the loading/not-found UI into the JSX return block, after all hook
calls are registered.

### Commit
Part of `3f96b73` — Fix drag-to-zone, preview priority, and PDF export bugs

See also: `.opencode/plans/fix-builder-cv-not-found.md` (detailed plan with diff spec)

## Verification


## Follow-up

<!-- Migrated from BUG-01KYZ1D27H4YVHPY977NX7HWGQ during the schema-4 cutover. -->
