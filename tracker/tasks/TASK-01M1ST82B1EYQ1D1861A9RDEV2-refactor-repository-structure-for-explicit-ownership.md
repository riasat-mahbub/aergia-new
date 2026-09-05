---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1ST82B1EYQ1D1861A9RDEV2
TYPE: task
STATUS: PLANNED
PRIORITY: Medium
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS:
- architecture
- repository-structure
- frontend
- backend
- documentation
RELATIONS:
  related:
  - FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT
  - FEAT-01M1QRT0VH26RTPBDYSYQ8WQXT
  - TASK-01M1PT0PPNNTES6JFD3KS60Q2M
  - FEAT-01M1G4FG0YGJB1XWBMDGV0PDTM
AFFECTS:
  files:
  - AGENTS.md
  - README.md
  - api/
  - web/
  - agent/
  - contracts/
  - tailoring-skill/
  - docs/plans/
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-05T22:15:25.281692+00:00'
UPDATED_AT: '2026-09-05T22:15:25.281692+00:00'
---

# Refactor repository structure for explicit ownership

## Background

Reorganize the frontend around TanStack routes, product features, and shared code; package the tailoring skill with its contracts; split subsystem guidance; clarify backend schema names; and expose development OpenAPI documentation without changing product behavior.

## Investigation

The current backend and renderer layout is mostly clear, but `app.schema` and
`app.schemas` have different responsibilities that their names do not show.
The frontend currently keeps TanStack file routes in `web/src/routes` while
page implementations use a Next-shaped `web/src/app` tree. This makes route
ownership unclear and reflects a possible future framework rather than the
current TanStack Start runtime. The portable tailoring contracts are used by
the tailoring skill and backend compatibility tests, so they can move into a
renamed `tailoring-skill` package without changing the protocol. FastAPI
already produces OpenAPI 3.1, but its default documentation URLs do not use
the public `/api` gateway and most operations are not grouped by tags.


## Decision

Keep TanStack route definitions in `web/src/routes`, move product ownership to
`web/src/features`, and move cross-feature code to `web/src/shared`. Remove
`web/src/app` after route adapters import feature public APIs. Rename `agent`
to `tailoring-skill` and place the tailoring JSON Schemas and fixtures inside
it. Rename backend `schema` to `document_schema` and `schemas` to
`http_schemas`. Split human and coding-agent guidance by subsystem. Expose
tagged Swagger/OpenAPI endpoints only outside production.


## Implementation

The authoritative step-by-step plan is
`docs/plans/2026-09-05-self-documenting-repository-structure.md`. The work is
split into small commits with verification after every structural slice. The
plan explicitly supersedes the earlier `web/src/app` ownership direction; a
future Next.js migration requires a new decision and plan.


## Verification

Planning verification: current worktree was clean at baseline `d0f78fe`;
tracker validation reported zero errors and three pre-existing fork warnings.
Implementation verification is defined in the plan and includes Ruff, pytest,
frontend architecture checks, lint, typecheck, codegen drift, production
build, tailoring Node tests, live OpenAPI checks, and `./dev.sh --smoke`.


## Follow-up

The frontend test-suite redesign remains separate. Do not use this structural
refactor to restore, replace, or reorganize that suite.
