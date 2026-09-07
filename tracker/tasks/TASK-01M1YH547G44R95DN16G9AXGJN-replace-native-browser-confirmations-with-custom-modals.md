---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M1YH547G44R95DN16G9AXGJN
TYPE: task
STATUS: IN_PROGRESS
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- frontend
- ux
- accessibility
RELATIONS: null
AFFECTS:
  files:
  - web/eslint.config.js
  - web/src/shared/ui/Modal.tsx
  - web/src/shared/ui/ConfirmModal.tsx
  - web/src/features/applications/pages/ApplicationListPage.tsx
  - web/src/features/applications/pages/ApplicationDetailPage.tsx
  - web/src/features/library/pages/LibraryPage.tsx
  - web/src/features/builder/hooks/useTemplateManifest.ts
  - web/src/features/builder/components/BuilderWorkspace.tsx
  - web/src/features/builder/components/customization/Inspector.tsx
  - web/src/features/builder/components/customization/controls/ResetFooter.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-07T18:12:43.888220+00:00'
UPDATED_AT: '2026-09-07T18:12:43.888220+00:00'
---

# Replace native browser confirmations with custom modals

## Background

Replace the four native browser confirm() dialogs used for template switching, application deletion, and library deletion with accessible Aergia custom confirmation modals. Preserve the browser-native beforeunload warning for tab close or refresh with unsaved builder changes.

## Investigation

The frontend had native confirmations for template switching and deleting
applications or library entries. The existing shared ``Modal`` component was
available but did not provide dialog semantics, focus management, or a common
confirmation API. The builder's ``beforeunload`` blocker is retained because
tab-close and refresh prompts must be browser-native.

## Decision

Use a shared ``ConfirmModal`` with async busy handling and error callbacks,
built on the existing modal surface. Keep destructive operations in their
feature pages and keep the template application hook free of UI concerns.

## Implementation

Added accessible dialog semantics, focus trapping/restoration, and initial
focus support to ``Modal``. Added ``ConfirmModal`` and wired it to application
list/detail deletion, library deletion, and builder template switching. Added
the ESLint ``no-alert`` guard and preserved the native ``beforeunload`` path.

## Verification

Frontend lint and typecheck pass; lint retains only the repository's existing
hook warnings. Architecture fixture/check tests and the production build pass.
The source audit finds no native ``alert``, ``confirm``, or ``prompt`` calls;
the only remaining browser-native prompt is the intentional
``enableBeforeUnload`` behavior.

## Follow-up

Run the live smoke gate and manually verify cancel/confirm, focus behavior,
async failure recovery, and double-submit prevention in each flow.
