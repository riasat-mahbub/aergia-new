---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2V140YQYJDZNV6P5KDFZ5JD
TYPE: feature
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS:
  files:
  - portfolio-showcase/proposals/workspace-directions.html
  - portfolio-showcase/proposals/workspace-directions.png
  - portfolio-showcase/proposals/workspace-directions-mobile.png
  - portfolio-showcase/proposals/README.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-18T19:50:29.079376+00:00'
UPDATED_AT: '2026-09-18T19:50:29.079376+00:00'
---

# Workspace visual design directions

## Background

Created a static design board comparing Atlas Workbench and Paper Desk treatments for every authenticated and public utility page, grounded in real Aergia showcase captures. This is proposal-only and does not change live routes.

## Investigation

The existing authenticated pages use a separate light Tailwind card language,
while the new public home page uses the Product Atlas system. The product has
nine meaningful surfaces beyond home: dashboard, CVs, builder, Library,
applications, application detail, settings, authentication, and the agent
tailoring handoff. Each has a different density and should not be flattened
into one generic landing-page treatment.

## Decision

Compare two shared shells—Atlas Workbench and Paper Desk—then assign each route
a task-specific treatment. Atlas Workbench is the working recommendation: dark
navigation rail, paper work surfaces, mint state/action color, editorial
metadata, a dense Builder, and generous public entry pages.

## Implementation

Added an isolated static proposal board with route-specific concepts, real
showcase screenshots, responsive CSS, and desktop/mobile rendered review
images. Updated the proposals README to explain the scope and preserve the
boundary that no live route is changed by this design work.

## Verification

Rendered with headless Chromium at 1440px and 390px widths. The HTML loads all
six referenced product captures, reports no console errors, and has no
horizontal overflow at either width. Desktop output is 1440x4803 and mobile
output is 390x10214.

## Follow-up
