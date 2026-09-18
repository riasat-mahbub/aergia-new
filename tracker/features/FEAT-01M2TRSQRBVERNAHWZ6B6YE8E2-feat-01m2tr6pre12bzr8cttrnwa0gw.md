---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2TRSQRBVERNAHWZ6B6YE8E2
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
  - media
RELATIONS:
  supersedes:
  - FEAT-01M2TR6PRE12BZR8CTTRNWA0GW
AFFECTS:
  files:
  - web/src/features/home/HomePage.tsx
  - web/public/showcase/demo-cv.webp
  - web/public/showcase/collect-import.webp
  - web/public/showcase/compose-editor.webp
  - web/public/showcase/customize-editor.webp
  - web/public/showcase/tailor-application.webp
  - web/public/showcase/exported-cv.webp
  - web/public/showcase/chapters/01-collect.webm
  - web/public/showcase/chapters/01-collect.mp4
  - web/public/showcase/chapters/02-compose.webm
  - web/public/showcase/chapters/02-compose.mp4
  - web/public/showcase/chapters/03-tailor.webm
  - web/public/showcase/chapters/03-tailor.mp4
  - web/public/showcase/chapters/04-move.webm
  - web/public/showcase/chapters/04-move.mp4
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-18T17:25:03.371574+00:00'
UPDATED_AT: '2026-09-18T17:25:03.371574+00:00'
---

# FEAT-01M2TR6PRE12BZR8CTTRNWA0GW

## Background

Follow-up: replace synthetic home-page panels with a real cropped demo CV hero, add four time-bounded showcase chapters (Collect, Compose, Tailor, Move) with real cropped screenshots, and link the footer/header to rmahbub.com. Verified desktop/mobile browser rendering and media responses.

## Investigation

The first landing-page pass used a fabricated CV illustration and one full
product-tour video in the hero. The showcase recording is 63 seconds long and
already has four meaningful product chapters: collection/import, composition
and customization, Library/application tailoring, and final review/export.
The recording also contains a clean demo CV and useful application surfaces
that can be shown as exact crops.

## Decision

Use the actual fictional showcase session as the visual source of truth. Put a
cropped demo CV in the hero, split the recording into four browser-friendly
chapter clips, and pair each clip with a real cropped frame and copy describing
the corresponding capability. Link the maker credit to `rmahbub.com`.

## Implementation

Extracted the demo CV and five feature frames from the showcase video. Created
WebM and MP4 chapter clips for `Collect` (0–13s), `Compose` (13–40s),
`Tailor` (40–55s), and `Move` (55–63s). Reworked `HomePage` so the hero uses
the real CV, each chapter has its own video player/poster/screenshot, and the
header/footer expose the maker link.

## Verification

`npm run lint` passed with the repository's existing nine hook-dependency
warnings and no errors. `npm run typecheck`, `npm run architecture:check`, and
`npm run build` passed. Playwright rendered the page at 1440×1000 and 390×844
with HTTP 200, four video players, the real CV image, and the maker link. The
extracted WebP/MP4/WebM assets returned HTTP 200 with the expected content
types.

## Follow-up

Regenerate the crops and chapter clips if the portfolio showcase storyboard or
demo fixture changes.
