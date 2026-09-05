---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M1QQX2ZKE6Q05G3MKKKFRBGR
TYPE: feature
STATUS: PLANNED
PRIORITY: Medium
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS:
- frontend
- architecture
- refactor
RELATIONS:
  depends_on:
  - FEAT-01M1PT8A0VE6WB4TC3Q7PZWF1H
AFFECTS:
  files:
  - docs/plans/2026-09-04-frontend-boundary-solid-refactor.md
  - web/scripts/check-frontend-boundaries.mjs
  - web/src/app/router.tsx
  - web/src/app/builder/[id]/page.tsx
  - web/src/app/builder/[id]/_components/ContentSectionList.tsx
  - web/src/app/dashboard/applications/[id]/page.tsx
  - web/src/components/common/DateField.tsx
  - web/src/components/common/section-editors/rich-text/
  - web/src/contracts/
  - web/src/lib/cv/
  - web/src/lib/llm/
  - web/src/services/
  - web/src/store/
  - AGENTS.md
LINKS:
  plan: local://docs/plans/2026-09-04-frontend-boundary-solid-refactor.md
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-05T02:55:59.475300+00:00'
UPDATED_AT: '2026-09-05T02:55:59.475300+00:00'
---

# Frontend boundary and SOLID decomposition

## Background

Follow-on to page-oriented ownership: finish route-state ownership, strengthen contracts and service boundaries, add route code splitting, and decompose high-coupling frontend modules without changing product behavior.

## Investigation

The post-migration import graph confirms that most top-level UI modules are
genuinely shared. Remaining ownership leaks are concentrated in Builder-only
state inside the global CV store, reactive LLM credential state under pure
`lib`, route-only library selectors in a global store, broad CV/library wire
contracts, and services that also own presentation mappings or browser/store
side effects. The router eagerly imports all pages and currently produces one
approximately 1.17 MB JavaScript bundle before gzip.

## Decision

Execute the follow-on as dependency-ordered phases: establish pure domain and
contract seams, correct state ownership, purify services, decompose Builder and
other high-coupling components, then add route lazy loading and stricter
architecture enforcement. Preserve Vite/React Router and all current behavior;
the actual Next.js runtime conversion remains separate.

## Implementation

See `docs/plans/2026-09-04-frontend-boundary-solid-refactor.md` for file-level
steps, acceptance criteria, test prerequisites, verification, and rollback.

## Verification

Planning baseline: architecture check, lint, codegen drift check, and Vite
production build pass. Tracker validation reported zero errors and three
pre-existing fork warnings. No application code changed while creating this
plan.

## Follow-up

Create bounded implementation tasks from the plan phases when work begins and
append tracker updates after each phase. Coordinate the focused characterization
tests with the separately deferred frontend testing reset before high-risk
Builder and rich-text extraction.
