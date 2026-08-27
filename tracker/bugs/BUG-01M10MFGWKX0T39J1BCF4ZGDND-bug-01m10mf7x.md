---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M10MFGWKX0T39J1BCF4ZGDND
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01M10MF7XHAV0WNYHTWYR55H9S
AFFECTS:
  files:
  - api/app/schemas/library.py
  - api/app/services/library.py
  - api/tests/test_library.py
  - web/src/lib/api/library.ts
  - web/src/components/library/LibraryCreateModal.tsx
  - web/src/components/library/LibraryPicker.tsx
  - web/src/components/library/LibraryEntryCard.tsx
  - web/src/components/sections/_shared/EntryAddRow.tsx
  - web/src/pages/BuilderPage.tsx
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-27T03:33:37.299275+00:00'
UPDATED_AT: '2026-08-27T03:33:37.299275+00:00'
---

# BUG-01M10MF7X

## Background

Centralized CV section ↔ Library kind mapping in app.schemas.library and web/src/lib/api/library.ts; applied promotion, add, clone, picker, modal, and card paths. Backend library plus renderer tests: 103 passed; frontend Vitest: 317 passed.

## Investigation

Renderer and parser contracts use plural section types; Library storage and API kinds are singular. Existing promotion and add-to-library code compared these values directly, while cloning returned singular section types. Frontend library creation also passed singular kinds to a plural-only editor registry.

## Decision

Keep Library wire kinds singular and translate at the service/UI boundary. Accept legacy singular CV section aliases on the backend, but always emit renderer-supported plural types when cloning or selecting an entry.

## Implementation

Added shared mapping helpers per runtime boundary; applied them to promotion, per-entry add, clone, picker, modal editor creation, and entry-card field summaries. Added a Promote button to the builder header.

## Verification

Backend library, builder, and renderer tests: 103 passed. Frontend Vitest: 317 passed. Codegen drift check passed. Full backend suite still has unrelated pre-existing failures from persistent test data and smoke mocks.
## Follow-up
