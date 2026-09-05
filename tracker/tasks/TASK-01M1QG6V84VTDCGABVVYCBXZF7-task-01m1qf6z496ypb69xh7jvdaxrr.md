---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1QG6V84VTDCGABVVYCBXZF7
TYPE: task
STATUS: IN_PROGRESS
PRIORITY: Medium
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01M1QF6Z496YPB69XH7JVDAXRR
AFFECTS:
  files:
  - web/src/components/common/section-editors
  - web/src/components/common/DateField.tsx
  - web/src/components/common/SortableAccordionList.tsx
  - web/src/components/library/AddFromLibraryButton.tsx
  - web/src/components/profile/UserProfileEditor.tsx
  - web/src/lib/cv/types.ts
  - web/src/lib/customization
  - web/src/lib/forms/useFieldArray.ts
  - web/src/lib/rich-text/transform.ts
  - web/src/app/builder/[id]/components/ContentSectionList.tsx
  - web/src/app/dashboard/settings/components/SettingsProfileCard.tsx
  - web/src/app/dashboard/library/components/LibraryProfileCard.tsx
  - web/src/contracts
  - web/src/services/library.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-05T00:41:30.628926+00:00'
UPDATED_AT: '2026-09-05T00:41:30.628926+00:00'
---

# TASK-01M1QF6Z496YPB69XH7JVDAXRR

## Background

Implemented the frontend module-boundary refactor: section editors and UI primitives now live under components/common, CV/style/rich-text/form helpers moved to responsibility-based lib folders, Library controls are injected by the builder host, profile editing is controlled through UserProfileEditor, settings and Library own separate profile cards, and the section registry is closed and typed.

## Investigation


## Decision


## Implementation

Moved section editors into `components/common/section-editors`, with a closed
`SectionType` registry and host-injected entry actions. Library UI remains in
`components/library`, so common editors no longer depend on that feature.
Moved data, customization, rich-text, and generic form helpers into
responsibility-based `lib` folders. Replaced the shared synthetic-instance
profile card with a controlled `UserProfileEditor` and independent Settings
and Library cards while retaining the single `profileStore`.

## Verification

`npm run build` passed. `npm run lint` passed with three React hook dependency
warnings. `npm run codegen:check` and `git diff --check` passed. No frontend
test files or test script are currently present in `web`.

## Follow-up
