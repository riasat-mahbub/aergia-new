---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M153RSR27FZSGA9QJJ602FBK
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: riasat
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M153GZE2DA4C03RZ1TA1QET0
AFFECTS:
  files:
  - web/src/components/applications/RelevanceDrawer.tsx
  - web/src/pages/ApplicationDetailPage.tsx
  - web/src/pages/BuilderPage.tsx
  - web/src/pages/__tests__/ApplicationDetailPage.test.tsx
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-28T21:17:47.650268+00:00'
UPDATED_AT: '2026-08-28T21:17:47.650268+00:00'
---

# FEAT-01M153GZE2DA4C03RZ1TA1QET0

## Background

Moved the relevance evidence drawer to the linked CV builder: its relevance chip now opens the drawer while editing, and application detail provides a link to inspect evidence in the builder.

## Investigation


## Decision


## Implementation

The builder’s linked-application context now derives a typed relevance result
and opens the existing right-side drawer from the relevance score chip. The
application detail page keeps a compact relevance summary and links to the
builder for the full analysis.

## Verification

The focused application-detail and builder tests pass, and the production
frontend build passes.

## Follow-up
