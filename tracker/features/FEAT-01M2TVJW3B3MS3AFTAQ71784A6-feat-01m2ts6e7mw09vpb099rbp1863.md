---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2TVJW3B3MS3AFTAQ71784A6
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
  - FEAT-01M2TS6E7MW09VPB099RBP1863
AFFECTS:
  files:
  - web/src/features/home/HomePage.tsx
  - web/public/showcase/application-detail.webp
  - web/public/showcase/builder.webp
  - web/public/showcase/customize.webp
  - web/public/showcase/dashboard.webp
  - web/public/showcase/imported.webp
  - web/public/showcase/library.webp
  - web/public/showcase/pipeline.webp
  - web/public/showcase/tailored.webp
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-18T18:13:44.171402+00:00'
UPDATED_AT: '2026-09-18T18:13:44.171402+00:00'
---

# FEAT-01M2TS6E7MW09VPB099RBP1863

## Background

Implementing the approved expanded Product Atlas homepage in the live HomePage feature with real showcase media and auth-aware CTAs.

## Investigation

The approved Product Atlas proposal communicates the complete product through
real screens and distinct Author, Remember, and Pursue chapters. The previous
live home page still used synthetic UI in its feature section and did not show
the actual dashboard, Library, application detail, relevance, tailoring, or
quality/export context.

## Decision

Adapt the expanded atlas directly into the existing home feature. Keep the
dark product-led direction, make personal attribution subtle, preserve the
existing auth-aware routes, and use only real showcase captures for interface
imagery.

## Implementation

Replaced the public HomePage with the responsive Product Atlas structure:
connected-system map; annotated builder anatomy; import and customization
captures; Library categories and source/reuse explanation; application detail,
relevance, status/follow-up, standard tailoring, coding-agent tailoring, trust
principles, product tour, and final CTA. Added the real showcase frame assets
under `web/public/showcase/`. Header and footer link to `rmahbub.com` with a
quiet treatment.

## Verification

Passed `npm run lint` (existing warnings only), `npm run typecheck`,
`npm run architecture:test`, `npm run architecture:check`,
`npm run codegen:check`, and `npm run build`. Browser-checked the route at
1440px and 390px: no horizontal overflow, no missing loaded media, and the
product-tour video is present.

## Follow-up

Run the normal `./dev.sh --smoke` release gate before merging this homepage
implementation.
