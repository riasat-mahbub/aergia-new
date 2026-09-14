---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2H25ZQ1C0PQ4MK015HJDR2T
TYPE: feature
STATUS: DONE
PRIORITY: Low
SEVERITY: null
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS:
- frontend
- library
- ux
RELATIONS: null
AFFECTS:
  files:
  - web/src/features/library/components/LibraryKindGroup.tsx
  - web/src/features/library/pages/LibraryPage.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-14T22:56:37.601949+00:00'
UPDATED_AT: '2026-09-14T22:56:37.601949+00:00'
---

# Open library editor from its kind group

## Background

Clicking Add within an existing Library kind group should open a preselected editor for that kind. The general Add entry button should continue to show the kind picker.

## Investigation

Each Library group already has its `kind`, but its Add callback accepted no
arguments. The page therefore opened the modal without `initialKind`, making
the user choose the same kind again.

## Decision

Pass the clicked group's kind into the create modal. Keep page-level Add
actions unscoped so they continue to offer the kind picker.

## Implementation

The group Add callback now receives its `LibraryEntryKind`. `LibraryPage`
stores that optional kind and passes it to `LibraryCreateModal`, clearing it
when the modal closes or an existing item is edited.

## Verification

In headless Chromium, confirmed general Add still displayed the kind picker.
Projects-group Add opened directly to the Projects editor; saving produced a
`project` Library entry with exactly one payload record. Typecheck and
frontend architecture checks passed. Lint had no errors and reported nine
existing hook-dependency warnings elsewhere.

## Follow-up
