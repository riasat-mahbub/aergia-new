---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M28QAX2PNZCE1BT8YHZ5EP9P
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: High
TAGS: null
RELATIONS:
  related:
  - TASK-01M0X609VN4A8KNDEAS9V9SAYA
AFFECTS:
  files:
  - web/src/features/builder/components/customization/SectionInspector.tsx
  - web/src/features/builder/components/customization/groups/AppearanceGroup.tsx
  - web/src/features/builder/components/customization/groups/BodyTextGroup.tsx
  - web/src/features/builder/components/customization/groups/Controls.tsx
  - web/src/features/builder/components/customization/groups/FieldOverridesGroup.tsx
  - web/src/features/builder/components/customization/groups/HeadingGroup.tsx
  - web/src/features/builder/components/customization/groups/LayoutGroups.tsx
  - web/src/features/builder/components/customization/groups/SpacingGroup.tsx
  - web/src/features/builder/components/customization/groups/stylePatches.ts
  - web/src/features/builder/components/customization/groups/types.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-11T17:13:08.950459+00:00'
UPDATED_AT: '2026-09-11T17:13:08.950459+00:00'
---

# Split builder section style inspector into focused groups

## Background

Refactor the builder's section style inspector into focused group components while preserving the existing SectionInstanceStyle JSON contract, inheritance cleanup, and control behavior.

## Investigation

The inspector was a single 484-line component. Its controls edited the
typed `SectionInstanceStyle` object and delegated final style resolution to
the backend, but presentation, section visibility rules, and patch cleanup
were all interleaved in one file.


## Decision

Keep the existing wire/schema contract and backend cascade. Extract focused
React group components and shared patch/control helpers; keep the parent as
the adapter that owns inheritance-safe updates.


## Implementation

Extracted heading, appearance, body text, spacing, page-break/date/alignment,
and field override groups. Centralized axis, typography, field-style, token,
and cleanup helpers under the groups directory. Preserved existing labels,
test IDs, reset behavior, and section-type visibility rules.


## Verification

`cd web && npm run typecheck` passed.

`cd web && npm run lint` passed with the repository's existing nine React hook
dependency warnings and no errors.

`cd web && npm run architecture:test && npm run architecture:check` passed.


## Follow-up
