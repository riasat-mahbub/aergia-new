---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1PQG21SWJTN33D5DP9N697C
TYPE: task
STATUS: PLANNED
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT
AFFECTS:
  files:
  - web/src/pages/SettingsPage.tsx
  - web/src/pages/__tests__/SettingsPage.test.tsx
  - web/src/components/builder/LLMKeyDialog.tsx
  - web/src/components/profile/ProfileCard.tsx
  - web/src/main.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-04T17:29:38.106036+00:00'
UPDATED_AT: '2026-09-04T17:29:38.106036+00:00'
---

# Settings page ownership

## Background

Step 5. Move SettingsPage and settings-only dialogs/composition into a page feature boundary. Keep shared profile/editor code unchanged. Parent plan: FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT.

## Investigation


## Decision


## Implementation

- Move settings-only composition to `web/src/features/settings/`.
- Keep `ProfileCard` and section-editor dependencies shared when Library or Builder still consumes them.
- Preserve settings persistence, API-key dialogs, and route behavior.


## Verification


## Follow-up
