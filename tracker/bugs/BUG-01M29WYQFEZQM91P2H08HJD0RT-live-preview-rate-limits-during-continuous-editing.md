---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M29WYQFEZQM91P2H08HJD0RT
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS:
- live-preview
RELATIONS:
  related:
  - FEAT-01M20YH3CH8BEVHM0KJTZY7QAX
AFFECTS:
  files:
  - web/src/features/builder/api/render.ts
  - web/src/features/builder/components/preview/UserTemplateRenderer.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-12T04:10:35.886127+00:00'
UPDATED_AT: '2026-09-12T04:10:35.886127+00:00'
---

# Live preview rate-limits during continuous editing

## Background

The builder requested HTML preview renders immediately for every document state update, causing /render/html to reach its 30-per-minute client-IP limit during extended editing.

## Investigation

The preview effect posted on every `instances` or `customizations` change. Rich
text emits a change on every Lexical edit, so typing quickly could exceed the
HTML renderer's 30-request-per-minute client-IP limit. The previous cleanup
ignored stale responses but did not cancel the request.

## Decision

Keep editor and builder state updates immediate. Coalesce preview work after a
400 ms quiet period and enforce at least three seconds between preview request
starts, leaving a margin below the endpoint limit. Abort superseded requests
on the client.

## Implementation

Added the debounce and minimum request interval to the shared live preview, so
all content and style editors benefit. The render API wrapper now accepts an
optional abort signal.

## Verification

`npm run typecheck`, `npm run architecture:test`, `npm run architecture:check`,
`npm run build`, and `git diff --check` passed. `npm run lint` passed with nine
existing hook-dependency warnings.

## Follow-up
