---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1SRGEPMJZTBB8T643AZYAS8
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01M1SRAX0P5C6F9YNFN0QGJ4MV
AFFECTS:
  files:
  - web/src/app/builder/[id]/_hooks/useUnsavedChanges.ts
  - web/src/app
  - web/src/lib/routerCompat.tsx
  - api/app/app.py
  - web/package.json
  - dev.sh
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-05T21:45:02.932347+00:00'
UPDATED_AT: '2026-09-05T21:45:02.932347+00:00'
---

# TASK-01M1SRAX0P5C6F9YNFN0QGJ4MV

## Background

Final verification rerun after native blocker cleanup: the blocker now uses TanStack Router's resolver plus its dynamic before-unload predicate, preserving unsaved-change protection without the compatibility wrapper. Typecheck, build, lint, architecture, codegen, Ruff, shell syntax, and diff checks remain green; lint has only existing hook dependency warnings.

## Investigation

The direct TanStack Router blocker exposes a discriminated `status` and
optional resolver methods, unlike the deleted compatibility wrapper. Its
`enableBeforeUnload` option accepts a predicate, so the hook can keep the
browser prompt aligned with the current dirty state without a second window
listener.


## Decision

Use the native resolver and dynamic before-unload predicate. Keep Builder's
route-level SSR mode unchanged until its data-loading boundary is decided
explicitly.


## Implementation

Updated `useUnsavedChanges` to use `useBlocker({ withResolver: true })`, test
`status === "blocked"`, and delegate before-unload handling to the router.
Removed the stale manual listener and its compatibility dependency.


## Verification

`npm run typecheck`, `npm run build`, `npm run lint`, architecture fixtures and
checks, codegen drift check, Ruff, shell syntax, and diff checks pass. Lint
reports only the existing React-hook dependency warnings.


## Follow-up

The deferred replacement behavior suite and deployment work remain out of
scope. A direct decision is still needed on whether Builder remains
`ssr: "data-only"` or becomes client-only.
