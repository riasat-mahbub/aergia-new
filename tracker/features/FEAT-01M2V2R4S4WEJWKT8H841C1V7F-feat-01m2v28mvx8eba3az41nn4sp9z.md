---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2V2R4S4WEJWKT8H841C1V7F
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
  - FEAT-01M2V28MVX8EBA3AZ41NN4SP9Z
AFFECTS:
  files:
  - web/src/features/home/HomePage.tsx
  - web/src/features/home/HomePage.css
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-18T20:18:56.932623+00:00'
UPDATED_AT: '2026-09-18T20:18:56.932623+00:00'
---

# FEAT-01M2V28MVX8EBA3AZ41NN4SP9Z

## Background

Collapsing homepage text-heavy layouts to a maximum of two columns: section number and title now form the main column while supporting copy occupies the second; ledger rows and process/index groups also use two-column grids.

## Investigation

The section headers and feature ledgers placed a small section label, a large
heading, and supporting copy in three columns. The same pattern appeared in
the four-item navigation index and five-step process strip, making the text
feel scattered at desktop widths.

## Decision

Use no more than two columns for text-led groups. Keep the section number with
the main heading and place the subtitle in the second column; stack the same
relationship on mobile. Preserve multi-panel media compositions and the
system-flow diagram because those are visual product structures rather than
competing text columns.

## Implementation

Grouped section labels with their headings, grouped ledger titles with their
descriptions, changed the section index to two columns, and changed the
application process strip to two columns. Added responsive rules so mobile
returns to one readable column.

## Verification

Passed frontend lint (nine pre-existing hook warnings), TypeScript
type-checking, production build, architecture boundary checks, and headless
browser rendering. Desktop reports two 660px process/index columns; mobile
reports one process column and two index columns, with no horizontal overflow
or console errors.

## Follow-up
