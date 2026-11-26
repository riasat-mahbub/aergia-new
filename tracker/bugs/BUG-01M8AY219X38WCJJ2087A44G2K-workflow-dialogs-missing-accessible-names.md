---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M8AY219X38WCJJ2087A44G2K
TYPE: bug
STATUS: DONE
PRIORITY: Medium
SEVERITY: Medium
EFFORT: S
OWNER: null
CONFIDENCE: High
TAGS:
- frontend
- accessibility
- dialogs
RELATIONS:
  related:
  - TASK-01M1YH547G44R95DN16G9AXGJN
AFFECTS:
  files:
  - web/src/shared/ui/Modal.tsx
  - web/src/features/cvs/components/CreateCvModal.tsx
  - web/src/features/cvs/components/import/ImportCvModal.tsx
  - web/src/features/applications/components/ApplicationFormModal.tsx
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T03:23:18.205452+00:00'
UPDATED_AT: '2026-11-26T03:51:32.984783+00:00'
---

# CV and application dialogs lack accessible names

## Background

The shared modal accepts a heading ID and exposes a dialog role. Several primary workflow dialogs display a heading without passing its ID. Create New CV also displays a standalone Title label without associating it with the input.

## Investigation

1. Open **Create New CV** and **Import CV** from My CVs.
2. Open **Track an application** from Applications.
3. Inspect each dialog’s accessible name and the Create New CV Title input’s associated labels.

**Actual.** All three dialogs expose a dialog role without an accessible name. The Create New CV title input has zero associated labels.

**Expected.** Each dialog is named by its visible heading. The title input exposes **Title** as its name, and keyboard focus enters and returns to the expected control.

## Verification

Chromium verified the names of Create New CV, Import CV, Track an application, and Edit application. The Create New CV title field had its expected accessible name and initial focus. Tab stayed within each dialog in both directions, and Escape returned focus to its opener.

Confirmed the missing heading association for all three dialogs in Chromium on commit `78f71d2`. The Create New CV Title input reported an empty labels list.
