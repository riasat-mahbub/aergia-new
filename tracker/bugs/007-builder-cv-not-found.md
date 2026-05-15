---
ID:             007
TYPE:           bug
NAME:           BuilderPage "CV not found" stuck state
SUMMARY:        Early return guard before hooks prevents loadCV() from ever executing
STATUS:         CLOSED
TAGS:           builder, react, hooks, loading, early-return
LINKS:          fix-commit=3f96b73, opencode-plan=.opencode/plans/fix-builder-cv-not-found.md
---

## Description

The early return guard in BuilderPage.tsx was placed before all hook calls
(useState, useEffect). In React, hooks must run unconditionally on every
render. The guard prevented:

1. `useState` calls below the guard from being initialized
2. `useEffect` from being scheduled — this is where `loadCV(id)` lives

Flow: Component mounts with `isLoading=false`, `currentCV=null` →
Guard condition `isLoading || !currentCV` is true → returns early →
`useEffect` never runs → `loadCV()` never called → no API request →
Store state never changes → stuck on "CV not found" forever.

## Resolution

Removed the early return guard before hooks. Added a `showLoading` state
initialized to `true`. Set it to `false` after `loadCV()` completes.
Moved the loading/not-found UI into the JSX return block, after all hook
calls are registered.

### Commit
Part of `3f96b73` — Fix drag-to-zone, preview priority, and PDF export bugs

See also: `.opencode/plans/fix-builder-cv-not-found.md` (detailed plan with diff spec)
