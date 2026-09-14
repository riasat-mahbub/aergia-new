---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M2GNK7P9NGX7H170JCWK41B3
TYPE: bug
STATUS: DONE
PRIORITY: Medium
SEVERITY: Low
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS:
- frontend
- library
- modal
RELATIONS: null
AFFECTS:
  files:
  - web/src/features/library/components/LibraryCreateModal.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-14T19:16:40.265393+00:00'
UPDATED_AT: '2026-09-14T19:16:40.265393+00:00'
---

# First library edit opens the new-entry picker

## Background

Opening an existing Library entry for the first time shows the type picker instead of the edit form. The form opens correctly on later attempts.

## Investigation

The modal component was mounted while closed, so its form state initialized
without an entry. On the first open, an initialization ref caused the effect
to return before copying the selected entry's kind and payload into the form.
Subsequent opens passed that guard and displayed the edit form correctly.

## Decision

Initialize form state when a form instance is created for the selected entry.
Keep the modal shell mounted so its existing open and close behavior remains
intact.

## Implementation

Moved form state into a keyed child rendered while the modal is open. Its key
changes with the entry or initial kind, and its initial state is copied from
the selected entry immediately.

## Verification

`npm run typecheck`, `npm run lint`, `npm run architecture:test`,
`npm run architecture:check`, and `git diff --check` passed. Lint reports
nine existing hook dependency warnings outside the changed file.

## Follow-up
