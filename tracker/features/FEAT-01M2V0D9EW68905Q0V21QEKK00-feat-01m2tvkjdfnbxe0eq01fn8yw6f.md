---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2V0D9EW68905Q0V21QEKK00
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
  - FEAT-01M2TVKJDFNBXE0EQ01FN8YW6F
AFFECTS:
  files:
  - web/src/features/home/HomePage.tsx
  - web/src/features/home/HomePage.css
  - web/public/showcase/aergia-showcase-poster.webp
  - web/public/showcase/aergia-showcase.mp4
  - web/public/showcase/aergia-showcase.webm
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
CREATED_AT: '2026-09-18T19:38:04.124663+00:00'
UPDATED_AT: '2026-09-18T19:38:04.124663+00:00'
---

# FEAT-01M2TVKJDFNBXE0EQ01FN8YW6F

## Background

Correcting the homepage implementation after visual review showed that the approved Product Atlas proposal had been approximated rather than faithfully adapted. Replacing the compressed Tailwind translation with the proposal's exact structure and scoped production CSS, while retaining real Aergia media, auth-aware calls to action, and subtle author attribution.

## Investigation

The production page had been rewritten as a compact Tailwind approximation of
the approved expanded Product Atlas proposal. That translation changed the DOM,
introduced unapproved header controls, and replaced the proposal's exact 1320px
canvas, 900px breakpoint, media stages, image transforms, Arial metrics, and
section rhythm with loosely similar utility values. The result retained the
content but not the approved design.

## Decision

Treat `portfolio-showcase/proposals/concept-gallery-expanded.html` as the
implementation specification. Adapt its markup directly to React and move its
CSS into a feature-scoped stylesheet so the live page preserves the proposal's
visual system without leaking styles to the authenticated application. Keep the
only required product adaptations: auth-aware primary links, public showcase
asset paths, semantic image alternatives, and the subtle rmahbub.com header and
footer links.

## Implementation

Rebuilt `HomePage.tsx` around the proposal's original section structure and
class names, including the atlas hero, connected system map, authoring anatomy,
Library stage, application detail, two-path tailoring panel, trust ledger, real
product tour, and final call to action. Added `HomePage.css` as a scoped,
near-literal production adaptation of the proposal CSS. All product imagery and
video use real Aergia captures from `web/public/showcase`.

## Verification

Passed frontend lint (with nine pre-existing hook warnings outside the homepage),
TypeScript type-checking, architecture fixtures, architecture boundaries,
schema codegen check, and the production build. Headless Chromium rendered the
live page at 1440x1000 and 390x844 with no console errors, no horizontal
overflow, all eleven images loaded at their expected dimensions, and the tour
video present. Side-by-side full-page comparison aligned with the approved
proposal at both widths; live/proposal heights differ by only 40px on desktop
and 31px on mobile.

## Follow-up
