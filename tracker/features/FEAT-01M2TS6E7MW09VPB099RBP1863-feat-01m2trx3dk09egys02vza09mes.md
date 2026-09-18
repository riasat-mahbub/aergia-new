---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2TS6E7MW09VPB099RBP1863
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M2TRX3DK09EGYS02VZA09MES
AFFECTS:
  files:
  - web/src/features/home/HomePage.tsx
  - web/public/showcase/aergia-showcase-poster.webp
  - web/public/showcase/aergia-showcase.mp4
  - web/public/showcase/aergia-showcase.webm
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-18T17:31:59.604465+00:00'
UPDATED_AT: '2026-09-18T17:31:59.604465+00:00'
---

# FEAT-01M2TRX3DK09EGYS02VZA09MES

## Background

Rollback requested: restore the prior editorial home page with the full product-tour video, structured feature map, workflow band, and application preview. Remove the later four-chapter media and cropped screenshot set.

## Investigation


## Decision


## Implementation


## Verification

`npm run lint` passed with the repository's existing nine hook-dependency
warnings and no errors. `npm run typecheck`, `npm run architecture:check`,
`npm run build`, and `git diff --check` passed.


## Follow-up
