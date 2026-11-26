---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M8AY219XV55JCZZ8B84QANVK
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: High
TAGS:
- frontend
- ux
- implementation-plan
RELATIONS:
  related:
  - BUG-01M8AY219X52RZ6X8E18XEXFEQ
  - BUG-01M8AY219XA5YH1RQ61BMPS212
  - BUG-01M8AY219XH4B6JV8PXMM8Q9SB
  - BUG-01M8AY219XR582DZAG8Y4S8CVH
  - BUG-01M8AY219XEH2HRA09GSQ3H8D2
  - BUG-01M8AY219X38WCJJ2087A44G2K
AFFECTS:
  files:
  - docs/plans/2026-11-25-cv-workspace-ux-execution-plan.md
  - web/src/shared/api/client.ts
  - web/src/shared/ui/Modal.tsx
  - web/src/features/cvs/components/import/ImportCvButton.tsx
  - web/src/features/cvs/components/import/ImportCvModal.tsx
  - web/src/features/cvs/components/CreateCvModal.tsx
  - web/src/features/applications/components/ApplicationFormModal.tsx
  - web/src/app-shell/components/SiteNavbar.tsx
  - web/src/features/tailoring/api/tailoring.ts
  - web/src/features/tailoring/api/providers.ts
  - web/src/features/tailoring/components/TailoringProviderSettings.tsx
  - web/src/features/applications/components/detail/ApplicationCvPanel.tsx
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T03:23:18.205452+00:00'
UPDATED_AT: '2026-11-26T05:59:17.557+00:00'
---

# Fix blocked and misleading CV workspace workflows

## Background

The production build at `78f71d2` exposed six reproducible conflicts across CV import, tailoring, dialogs, and mobile navigation.

- [Provider setup dead end](../bugs/BUG-01M8AY219X52RZ6X8E18XEXFEQ-optional-tailoring-provider-setup-leads-to-dead-end.md)
- [Repeat PDF import submission](../bugs/BUG-01M8AY219XA5YH1RQ61BMPS212-pdf-import-dialog-allows-repeat-submission.md)
- [Clipped Create CV actions](../bugs/BUG-01M8AY219XH4B6JV8PXMM8Q9SB-create-cv-dialog-clips-actions-in-landscape.md)
- [False tailoring error toasts](../bugs/BUG-01M8AY219XR582DZAG8Y4S8CVH-empty-tailoring-lookups-show-error-toasts.md)
- [Hidden mobile destinations](../bugs/BUG-01M8AY219XEH2HRA09GSQ3H8D2-mobile-navbar-hides-workspace-destinations.md)
- [Unnamed workflow dialogs](../bugs/BUG-01M8AY219X38WCJJ2087A44G2K-workflow-dialogs-missing-accessible-names.md)

## Detailed fix plans

The [agent execution plan](../../docs/plans/2026-11-25-cv-workspace-ux-execution-plan.md) specifies the order, file changes, and acceptance checks for audit findings 1, 2, 4, and 6.

- [1. Gate optional tailoring provider setup by availability](TASK-01M8AYCJG9Z3K4CF44B1GF4G5S-gate-optional-tailoring-provider-setup-by-availability.md)
- [2. Lock PDF import and show progress in the dialog](TASK-01M8AYCJG91RNFW55JDNWVR6EC-lock-pdf-import-and-show-progress-in-the-dialog.md)
- [3. Keep Create CV actions visible on short viewports](TASK-01M8B5WGVA1HRQPP5AY9WAHQ35-keep-create-cv-actions-visible-on-short-viewports.md)
- [4. Handle expected empty tailoring reads without toasts](TASK-01M8AYCJG9TJQVK0JN6RKAYA44-handle-expected-empty-tailoring-reads-without-toasts.md)
- [5. Make all workspace destinations reachable on mobile](TASK-01M8B5WGVAJW4BPR9WBMCV2G5H-make-all-workspace-destinations-reachable-on-mobile.md)
- [6. Name CV and application dialogs](TASK-01M8AYCJG9GY9T4C5D2J74CW32-name-cv-and-application-dialogs.md)

## Decision

Keep current routes, API payloads, and the coding-agent tailoring flow. Contain provider UI on deployments without provider endpoints. Treat delivering and enabling the provider integration as a separate change after the documented pilot and end-to-end verification.

## Implementation

1. **Prevent repeat imports.** Pass the parent’s pending state into the import dialog. Show progress on the submit action and disable repeat activation. Guard the async handler itself before starting work so clicks and Enter cannot overlap. Keep the form data available on failure and release the guard for retry.
2. **Handle expected empty tailoring responses.** Give optional API calls a narrow way to suppress the shared error toast for expected 404s. Apply it to the latest-session lookup and the builder’s optional draft-context lookup. Preserve the builder’s handling of an unavailable pending draft and keep genuine CV fetch failures, authorization errors, and unexpected server failures visible.
3. **Gate the provider entry points.** Use the provider status result consistently on application detail and Settings. For a deployment without provider endpoints, remove dead setup and download actions, and avoid the generic error toast for that expected result. Show one retryable status for a transient lookup failure. Use status from a supported backend to enable only working connection and setup actions. Before enabling a provider, verify status, connect, callback, disconnect, download where applicable, and an actual session with draft review. For Gemini, include the [Canadian pilot](../../docs/plans/2026-11-25-gmail-monitor-private-doc-pilot.md).
4. **Fix dialog scrolling and naming together.** Give Create New CV one bounded scroll area and keep its actions reachable. Review existing scrollable dialog bodies so the shared fix does not add a second scroll area. Use each dialog’s visible heading as its accessible name and associate the Create New CV title label with the input. Preserve initial focus, Tab containment, Escape, and focus restoration.
5. **Expose workspace navigation on small screens.** Replace the clipped strip with a discoverable menu that can be opened by touch and keyboard. Keep active route indication, close the menu on selection and Escape, and return focus to its trigger after Escape. Match current desktop navigation and preserve the builder’s navbar opt-out.

## Verification

Chromium verified all six findings against the built workspace and disposable test data. The linked tasks record the browser results, including landscape CV creation and access to all five workspace destinations on mobile.

Frontend lint, typecheck, architecture checks and fixtures, and the production build passed. The release smoke gate and session, builder, review, and provider browser harnesses passed in WSL. The smoke gate used Ruff 0.12.12 in the isolated test environment after Ruff 0.17.6 reported 637 findings in unchanged backend files.

On Windows, the production build, frontend lint with one existing warning, architecture checks and fixtures, and the release smoke gate passed after the dialog and navbar fixes. Chromium verified the new interactions against the production build.

- Delay the import response in a mounted Chromium check. Repeated click and Enter should produce one upload and one create attempt. Cover both successful navigation and failure followed by a retry.
- Open an application with no tailoring history and an ordinary saved CV. Neither should show an error toast. Exercise an unavailable pending draft, a missing CV, and an unexpected server error to confirm each still reports its own state.
- Test provider status as absent, transiently failing, and available. Confirm the coding-agent path is usable, failed requests have one relevant error message, and setup or download actions are only offered when they work.
- At 740 × 360, 390 × 844, and desktop size, verify Create New CV actions are reachable by touch-equivalent scrolling and keyboard. Check named dialogs in Create CV, Import CV, and Track an application, and verify focus restoration after dismissal.
- At widths of 320 and 390 px, open all five workspace destinations from the header. Check menu focus, active route indication, desktop navigation, and the builder header.
- Run frontend lint, typecheck, architecture checks and fixture tests, then the repository smoke gate. Record verification against each report.
