---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M8AYCJG9GY9T4C5D2J74CW32
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: High
TAGS:
- frontend
- accessibility
- dialogs
RELATIONS:
  related:
  - BUG-01M8AY219X38WCJJ2087A44G2K
  - TASK-01M8AY219XV55JCZZ8B84QANVK
AFFECTS:
  files:
  - web/src/shared/ui/Modal.tsx
  - web/src/shared/ui/ConfirmModal.tsx
  - web/src/features/cvs/components/CreateCvModal.tsx
  - web/src/features/cvs/components/import/ImportCvModal.tsx
  - web/src/features/applications/components/ApplicationFormModal.tsx
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T03:29:03.497697+00:00'
UPDATED_AT: '2026-11-26T03:51:32.984783+00:00'
---

# Name CV and application dialogs

## Background

Implementation plan for [BUG-01M8AY219X38WCJJ2087A44G2K](../bugs/BUG-01M8AY219X38WCJJ2087A44G2K-workflow-dialogs-missing-accessible-names.md).

## Investigation

The shared modal already accepts a heading ID. The Create New CV, Import CV, and application form callers leave it unset. Create New CV also renders Title separately from its input and uses native `autoFocus`, which can move focus before the shared modal records the opener.

## Decision

Follow the existing `ConfirmModal` pattern. Derive accessible names from the visible headings and use the shared modal's focus API for the Create New CV title field. Keep this plan focused on semantics and keyboard behavior. The short-viewport layout issue is tracked [separately](../bugs/BUG-01M8AY219XH4B6JV8PXMM8Q9SB-create-cv-dialog-clips-actions-in-landscape.md).

## Implementation

1. Generate a stable heading ID with `useId` in each of the three callers. Put it on the existing heading and pass it as `titleId`. In the application form, the visible heading should name both create and edit modes.
2. Associate the Create New CV Title label and input with `htmlFor` and a unique ID. Supply that input as the shared dialog's `initialFocusRef` in place of native `autoFocus` so the shared dialog can capture the opener before moving focus.
3. Keep the Import CV and application form focus order, dismissal, and existing field associations. When combined with the import pending-state change, verify the import form remains operable by keyboard after a failed request.
4. Add focused browser assertions using the dialog role and accessible name. Include a targeted focus restoration check for the Create New CV flow, where the focus mechanism changes.

## Verification

Chromium located all four modes by dialog role and visible name. It verified the Create New CV Title label and initial focus, and checked forward and reverse Tab containment and focus restoration on Escape.

- Open the workflows by keyboard and locate dialogs named **Create New CV**, **Import CV**, **Track an application**, and **Edit application**.
- Within Create New CV, locate the textbox named **Title**, verify it receives initial focus, and confirm Escape returns focus to **+ New CV**.
- Check forward and reverse Tab containment and Escape focus restoration on Import CV and both application form modes. Reopen each dialog and verify the ID is neither missing nor duplicated.
