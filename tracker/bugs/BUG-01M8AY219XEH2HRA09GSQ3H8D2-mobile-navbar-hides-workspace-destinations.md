---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M8AY219XEH2HRA09GSQ3H8D2
TYPE: bug
STATUS: PROPOSED
PRIORITY: Medium
SEVERITY: Medium
EFFORT: S
OWNER: null
CONFIDENCE: High
TAGS:
- frontend
- responsive
- navigation
RELATIONS:
  related:
  - FEAT-01M1T1HE13NNW3KBFWBAMV79VQ
  - TASK-01M1T4CK4XBBETG797XE09F3SG
AFFECTS:
  files:
  - web/src/app-shell/components/SiteNavbar.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T03:23:18.205452+00:00'
UPDATED_AT: '2026-11-26T03:23:18.205452+00:00'
---

# Mobile navbar hides workspace destinations

## Background

The authenticated header lays out the brand, five destinations, and logout in one row. On mobile the destination list becomes a horizontal scroll area.

## Investigation

1. Sign in at a 390 × 844 viewport.
2. From a workspace page, locate **Applications** and **Settings** using the header in its initial state.
3. Repeat at 320 × 640.

**Actual.** At 390 px the navigation has 243 px available for roughly 486 px of links. Library is visibly clipped, and Applications and Settings are entirely offscreen. The header shows no visible affordance for reaching the remaining links. At 320 px the visible navigation is even narrower.

**Expected.** Every workspace destination can be discovered and reached with touch and keyboard through an obvious navigation control.

## Verification

Reproduced across Dashboard, My CVs, Library, Applications, and Settings in Chromium on commit `78f71d2`. At 390 px, geometry confirmed that both Applications and Settings had zero visible width inside the navigation.
