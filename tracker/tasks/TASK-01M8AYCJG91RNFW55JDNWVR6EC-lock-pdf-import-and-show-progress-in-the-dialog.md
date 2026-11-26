---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M8AYCJG91RNFW55JDNWVR6EC
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: High
TAGS:
- frontend
- cv-import
- ux
RELATIONS:
  related:
  - BUG-01M8AY219XA5YH1RQ61BMPS212
  - TASK-01M8AY219XV55JCZZ8B84QANVK
AFFECTS:
  files:
  - web/src/features/cvs/components/import/ImportCvButton.tsx
  - web/src/features/cvs/components/import/ImportCvModal.tsx
  - web/src/features/cvs/state/cvListStore.ts
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T03:29:03.497697+00:00'
UPDATED_AT: '2026-11-26T03:51:32.984783+00:00'
---

# Lock PDF import and show progress in the dialog

## Background

Implementation plan for [BUG-01M8AY219XA5YH1RQ61BMPS212](../bugs/BUG-01M8AY219XA5YH1RQ61BMPS212-pdf-import-dialog-allows-repeat-submission.md).

## Investigation

The parent owns the async parse-and-create operation and updates its launcher. The modal enables submit from the title and file alone. React state updates also leave a gap before a newly disabled button is rendered, during which another submit can reach the parent.

## Decision

Use the parent as the single owner of the operation. Keep a synchronous submission guard for correctness and pass its visible pending state to the modal for interaction and feedback.

## Implementation

1. In `ImportCvButton.tsx`, acquire a ref-based guard before reading import credentials or starting the first request. A second submit returns immediately. Hold the guard through parsing and CV creation, and release it in cleanup on success or failure. Retain the current in-memory key cleanup.
2. Pass `busy` to `ImportCvModal`. Disable the submit control and guard form submission while busy. Show **Importing…** in the dialog and announce progress through a status element. Prevent input and file changes while the request uses the submitted values.
3. Apply the same pending state to Close, Cancel, Escape, and backdrop dismissal. Keep focus within the dialog while it is busy and restore an actionable focus target on failure. Replace the permanently hidden spinner and its stale comment with the actual pending UI.
4. After success, close once and navigate with the returned CV ID. On parse or create failure, keep the modal open with the chosen file, title, and template, release the guard, and allow retry.

## Verification

Chromium verified one parse request and one create request during repeated activation, busy feedback exposed through a live status with focus inside the dialog, blocked dismissal, and successful retry after separate simulated parse and create failures. The successful retry used the real PDF parser and CV create API.

- Intercept and delay parsing in Chromium. Activate Import repeatedly with click and Enter. Assert one parse request and a visible, announced pending state.
- Release parsing and delay CV creation. Repeat activation and assert one create request. When it succeeds, assert one navigation to the created CV.
- Exercise parse failure and create failure independently. Assert the same title, template, and file survive, the form becomes actionable, and one new attempt is sent on deliberate retry.
- Verify dismissal is blocked while pending and works before submission and after failure.
