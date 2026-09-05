---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1SRAX0P5C6F9YNFN0QGJ4MV
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
  - TASK-01M1SMB5R20N9SAAZ022YFGMB7
AFFECTS:
  files:
  - AGENTS.md
  - api/app/app.py
  - api/tests/test_auth.py
  - dev.sh
  - web/package.json
  - web/scripts/remove-start-shell.mjs
  - web/src/app
  - web/src/lib/routerCompat.tsx
  - web/src/router.tsx
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-05T21:42:00.982767+00:00'
UPDATED_AT: '2026-09-05T21:42:00.982767+00:00'
---

# TASK-01M1SMB5R20N9SAAZ022YFGMB7

## Background

Completed the remaining deterministic cleanup: removed the obsolete Start shell-rewrite script and FastAPI SPA/static fallback, switched all route pages to native TanStack Router APIs, deleted routerCompat and dead AuthBoundary, enabled production NODE_ENV for the Start launch path, and refreshed repository/test guidance. Builder route SSR classification remains unchanged pending an explicit product decision.

## Investigation

The migration had already moved public UI serving to TanStack Start, but the
repository still carried compatibility code and documentation from the
FastAPI-served SPA. The generated Start output no longer contains an
`index.html` shell, so the shell-removal script had no remaining work. Native
TanStack Router APIs provide typed route params/search values and a typed
navigation blocker, making the compatibility wrapper unnecessary.


## Decision

Keep Nitro limited to the same-origin FastAPI gateway and keep request
security in the segmented TanStack Start middleware. Do not reclassify the
Builder route's `data-only` SSR boundary until its server-data contract is
explicitly chosen.


## Implementation

- Removed `web/scripts/remove-start-shell.mjs` from the build pipeline.
- Removed FastAPI's obsolete static mount and SPA catch-all.
- Replaced all `routerCompat` imports with native TanStack Router links,
  navigation, params/search hooks, and blockers; deleted the wrapper.
- Deleted the unused `AuthBoundary` compatibility component.
- Set `NODE_ENV=production` for the local production-like Start launch path.
- Updated `AGENTS.md` and the API auth test comment for the new ownership
  boundary.


## Verification

`npm run typecheck`, `npm run build`, `npm run lint`,
`npm run architecture:test`, `npm run architecture:check`, and
`npm run codegen:check` pass. `ruff check api/app api/tests/test_auth.py`,
`bash -n dev.sh scripts/smoke.sh`, and `git diff --check` pass. Lint reports
the existing React-hook dependency warnings but no errors.


## Follow-up

Choose whether Builder should remain `ssr: "data-only"` or become explicitly
client-only before changing its loader/data boundary. The full replacement
behavior suite and deployment work remain deferred.
