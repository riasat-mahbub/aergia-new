---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M2ZYE2F41JGESV4FDCGRGJ2P
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - TASK-01M2ZTT35MHHFNVWX3D9R065GE
AFFECTS:
  files:
  - api/app/document_schema/models.py
  - api/app/services/renderer/html_values.py
  - web/src/features/builder/components/customization/controls/TokenPicker.tsx
  - web/src/generated/schema.ts
  - web/src/styles/tokens.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-20T17:39:44.740199+00:00'
UPDATED_AT: '2026-09-20T17:39:44.740199+00:00'
---

# Add intermediate section spacing options

## Background

Close the section spacing gap between Tight at 4px and Comfortable at 24px by adding intermediate choices. Preserve existing token values and make spacing values explicit in the picker tooltips.

## Investigation

Section spacing jumped from Tight at 4px to Comfortable at 24px. The same
token type controls spacing before and after sections and gaps between entries
and fields. Zone padding has a separate token type and keeps its current scale.

## Decision

Add Snug (8px), Balanced (12px), and Roomy (16px). Keep existing values for
None, Tight, Comfortable, Loose, and Spacious so saved styles continue to
render as before.

## Implementation

Extended the document spacing vocabulary and renderer map, added the options
and pixel tooltips in the inspector, and regenerated the TypeScript schema.

## Verification

`npm run codegen:check` and `git diff --check` passed. Tests were not run.

## Follow-up
