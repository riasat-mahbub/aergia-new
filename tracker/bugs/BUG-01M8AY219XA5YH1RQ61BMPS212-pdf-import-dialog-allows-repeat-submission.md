---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M8AY219XA5YH1RQ61BMPS212
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: High
EFFORT: S
OWNER: null
CONFIDENCE: High
TAGS:
- frontend
- cv-import
- ux
RELATIONS:
  related:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN8T
AFFECTS:
  files:
  - web/src/features/cvs/components/import/ImportCvButton.tsx
  - web/src/features/cvs/components/import/ImportCvModal.tsx
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T03:23:18.205452+00:00'
UPDATED_AT: '2026-11-26T03:51:32.984783+00:00'
---

# PDF import dialog allows repeat submission

## Background

The import flow parses a PDF, creates a CV from the response, and opens the builder. The launcher behind the modal reflects the pending state, while the actionable control inside the modal keeps its original label and enabled state.

## Investigation

1. Open **My CVs → Import CV** and choose a valid PDF.
2. With the first upload response delayed, select **Import** twice.

**Actual.** The modal still shows an enabled **Import** button after the first click. Two upload requests are sent. Since each submission proceeds independently to CV creation on success, a retry click can start an unintended second create flow.

**Expected.** One upload and one create attempt per submission. The modal indicates progress and prevents repeat activation while pending. After failure, the user can retry with the selected file, title, and template intact.

## Verification

Chromium held parse and create requests open separately. Repeated form activation sent one request per stage, the pending action retained keyboard focus, and dismissal was blocked. After independent simulated parse and create failures, the same title, template, and file survived. A deliberate retry parsed the PDF, created a CV, and opened it in the builder.

Reproduced in Chromium on commit `78f71d2`. With an intercepted pending response, the second click produced a second `POST /api/v1/cvs/import/pdf`. The check used a simulated failure response and did not depend on duplicate CV creation.
