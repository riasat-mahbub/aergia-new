---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M2TSRCN0C1ACV054FJ3DRT4B
TYPE: task
STATUS: IN_PROGRESS
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- frontend
- design
- homepage
RELATIONS: null
AFFECTS:
  files:
  - portfolio-showcase/proposals/README.md
  - portfolio-showcase/proposals/concept-editorial.html
  - portfolio-showcase/proposals/concept-editorial.png
  - portfolio-showcase/proposals/concept-editorial-mobile.png
  - portfolio-showcase/proposals/concept-gallery.html
  - portfolio-showcase/proposals/concept-gallery.png
  - portfolio-showcase/proposals/concept-gallery-mobile.png
  - portfolio-showcase/proposals/assets/
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-18T17:41:47.809029+00:00'
UPDATED_AT: '2026-09-18T17:41:47.809029+00:00'
---

# Explore two Aergia home page design directions

## Background

Create two isolated, screenshotable home-page proposals that use real Aergia product media, distinguish the complete feature set, and link to rmahbub.com without changing the live home route.

## Investigation

The live home page already has an editorial Aergia palette and a full product
tour, but it uses synthetic interface approximations in its feature sections.
The showcase recording provides real screens for import, editing, live preview,
customization, Library reuse, application tracking, tailoring, and export.

The requested Impeccable skill was not installed in this session. The official
Impeccable guidance was used as the fallback: establish a persuasive page
hierarchy, group related content by user outcome, use color purposefully, and
avoid repeated generic cards or decorative fake product UI.

## Decision

Keep the live route unchanged while the direction is being selected. Produce
two comparable static prototypes with identical product truth but materially
different composition: an editorial, CV-led journey and a denser product atlas.
Use only fictional showcase data and real Aergia captures.

## Implementation

Added two responsive standalone HTML concepts, seven frames extracted from the
existing portfolio showcase, full desktop and mobile review renders, a feature
coverage matrix, and links to https://rmahbub.com in each concept.

## Verification

Rendered both concepts in headless Chromium at 1440px and 390px widths. Checked
the desktop and mobile screenshots visually, parsed both documents, and
verified all local image/video sources resolve.

## Follow-up

Choose one direction (or a specific hybrid) before adapting it to the React
home feature and production navigation/authentication states.
