---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2TR6PRE12BZR8CTTRNWA0GW
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
  - home
  - landing-page
  - showcase
RELATIONS: null
AFFECTS:
  files:
  - web/src/features/home/HomePage.tsx
  - web/public/showcase/aergia-showcase-poster.webp
  - web/public/showcase/aergia-showcase.webm
  - web/public/showcase/aergia-showcase.mp4
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-18T17:14:39.758516+00:00'
UPDATED_AT: '2026-09-18T17:14:39.758516+00:00'
---

# Redesign public home page

## Background

Replace the stale public home page with a feature-rich Aergia product story inspired by FlowCV's workflow-led landing page and Impeccable's intentional visual hierarchy. Reuse the existing portfolio showcase media.

## Investigation

The previous route presented one headline, one CTA, and six generic cards. The
existing product already supports import, live editing, styling, Library reuse,
application tracking, tailoring, relevance review, and PDF export, and the
portfolio-showcase folder contains a real product-tour recording. FlowCV's
landing page establishes a useful workflow-led content pattern, while
Impeccable emphasizes clear hierarchy, intentional restraint, and avoiding
repetitive card layouts.

## Decision

Make the public home page an editorial product tour: keep the Aergia token
palette, add a product-focused navigation, lead with the real showcase video,
explain the full workflow in four steps, and expose all major capabilities in
a structured feature map. Keep authenticated and anonymous CTAs routed to the
existing workspace and registration flows.

## Implementation

Replaced `HomePage` with a responsive landing page containing the product nav,
hero CTA, showcase video, source-CV visual, six capability areas, workflow
sequence, application/tailoring illustration, and final CTA. Copied the
existing showcase poster, WebM, and MP4 into `web/public/showcase/` so the
media is served by the web app.

## Verification

`npm run lint` passed with the repository's existing nine hook-dependency
warnings and no errors. `npm run typecheck`, `npm run architecture:check`, and
`npm run build` passed. A local Playwright check rendered the page at desktop
(1440×1000) and mobile (390×844) viewports with HTTP 200, the hero video
present, and the registration CTA available.

## Follow-up

Update the product-tour asset when the portfolio showcase narrative changes.
