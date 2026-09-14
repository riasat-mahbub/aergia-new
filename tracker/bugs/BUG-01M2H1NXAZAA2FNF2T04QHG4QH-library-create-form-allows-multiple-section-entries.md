---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M2H1NXAZAA2FNF2T04QHG4QH
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
RELATIONS: null
AFFECTS:
  files:
  - web/src/features/library/components/LibraryCreateModal.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-14T22:47:50.879350+00:00'
UPDATED_AT: '2026-09-14T22:47:50.879350+00:00'
---

# Library create form allows multiple section entries

## Background

Creating a Library item reused a CV section editor in section mode, exposing controls to add multiple records to the payload. A Library item should start and remain a single entry.

## Investigation

The modal passed `mode="section"` when creating a new item and `mode="library"`
only when editing. The section mode exposes an “Add …” control that appends
another record to the array payload.

## Decision

Use the existing library-specific editor mode for both creating and editing a
Library item.

## Implementation

The modal now always passes `mode="library"`, so its section editor renders
the compact single-item form and omits the section-level add control.

## Verification

In headless Chromium, opened Add entry → Projects, confirmed there was no
“Add Project” control, created a Project, and verified the saved Library
payload contained exactly one record. `npm run typecheck` passed and lint had
no errors (nine existing hook-dependency warnings elsewhere).

## Follow-up
