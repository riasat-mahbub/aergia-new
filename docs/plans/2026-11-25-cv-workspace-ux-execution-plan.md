# CV workspace UX implementation plan

Implement findings **4, 1, 2, and 6** from the November 25 audit in that order. A single coding agent can execute the full plan. The suggested execution profile is `gpt-6-luna` with `max` reasoning. Finding numbers refer to the original six findings.

> Implement this plan from start to finish in the Aergia checkout. Read the repository instructions, preserve existing work, and verify each finding before continuing. Finish with the changed files, check results, and any unresolved acceptance criteria.

## Before editing

- Read [AGENTS.md](../../AGENTS.md) and [web/AGENTS.md](../../web/AGENTS.md). Run `git status --short` and inspect changes in your assigned files. The reports were reproduced at `78f71d2`. Use the current checkout and incorporate any fix already present.
- Search the tracker for the topics and check affected files with `tracker affects <file>`. The [tracker task](../../tracker/tasks/TASK-01M8AY219XV55JCZZ8B84QANVK-fix-blocked-and-misleading-cv-workspace-workflows.md) links the source reports and owns the overall status. If the installed tracker cannot read Schema 4, search the Markdown records and record the version limitation.
- Scope the product diff to the files below and focused regression coverage. Preserve routes, API response shapes, persisted state, and the existing CV and tailoring flows. The provider work controls frontend availability. Provider transport and production enablement follow the [Gemini pilot](2026-11-25-gmail-monitor-private-doc-pilot.md) and their own end-to-end verification. The [short-viewport dialog issue](../../tracker/bugs/BUG-01M8AY219XH4B6JV8PXMM8Q9SB-create-cv-dialog-clips-actions-in-landscape.md) and [mobile navbar issue](../../tracker/bugs/BUG-01M8AY219XEH2HRA09GSQ3H8D2-mobile-navbar-hides-workspace-destinations.md) have separate reports.
- Use a disposable account and fictional CV/PDF fixtures. Keep credentials, callback values, and tailoring capabilities out of logs and artifacts. Use `apply_patch` for hand edits.

| Order | Finding | Dependency |
| --- | --- | --- |
| 1 | **4. Expected empty tailoring responses show errors** | Establishes the API client option used by finding 1 |
| 2 | **1. Provider setup leads to a dead end** | Uses the error option from finding 4 |
| 3 | **2. PDF import can submit twice** | Independent |
| 4 | **6. Workflow dialogs lack accessible names** | Shares the import modal with finding 2 |

## Finding 4 Expected empty tailoring responses

**Files** `web/src/shared/api/client.ts`, `web/src/features/tailoring/api/tailoring.ts`, `web/src/features/tailoring/hooks/useTailoringSession.ts`, and `web/src/features/builder/hooks/useBuilderApplicationContext.ts`. [Tracker task](../../tracker/tasks/TASK-01M8AYCJG9TJQVK0JN6RKAYA44-handle-expected-empty-tailoring-reads-without-toasts.md)

1. Add one optional, typed request setting to the shared Axios client. Use `errorToast?: "local" | { ignoreStatuses: readonly number[] }`. Omitting the setting keeps current behavior. `"local"` delegates displayed error feedback to the caller. `ignoreStatuses` suppresses the global toast only for listed HTTP statuses.
2. Read the setting at the point where the interceptor calls the global reporter. Preserve the original rejected error, the 401 refresh and retry path, and the unauthorized handler. Avoid URL matching or changing Axios success criteria.
3. Give `getLatestTailoringSession` and `getTailoringDraftContext` an optional options object with `quietNotFound`. Translate `{ quietNotFound: true }` to `{ ignoreStatuses: [404] }` in the feature API module. Pass it only from the initial session hydration and the initial draft-context probe. The session-conflict recovery call and existing pending-draft refresh keep their default reporting.
4. Keep the initial builder fallback to ordinary and application-linked CV context. Preserve route and request generation guards. The primary CV fetch still owns the missing-CV error, and the pending-draft refresh still owns the draft-unavailable state.

**Pass criteria**

- On an existing application with no sessions, a 404 on `GET /api/v1/applications/<id>/tailoring-sessions/latest` leaves the application usable with no error toast.
- On an ordinary saved CV, a 404 on `GET /api/v1/cvs/<id>/tailoring-context` leaves the preview and editor usable with no error toast. A CV linked to the application still loads scanner context.
- Repeat each optional request with 403 and 503. The error follows its normal reporting path. A primary CV GET returning 404 still displays its load error. A 404 while refreshing a known draft still takes the existing recovery path.
- Use the actual Axios interceptor and global error handler for these assertions. The existing mounted harnesses cover route and session behavior but mock the tailoring API.

## Finding 1 Provider availability

**Files** `web/src/features/tailoring/api/providers.ts`, `web/src/features/tailoring/hooks/useTailoringProviders.ts`, `web/src/features/tailoring/components/TailoringProviderSettings.tsx`, `web/src/features/applications/pages/ApplicationDetailPage.tsx`, and `web/src/features/applications/components/detail/ApplicationCvPanel.tsx`. Use the tailoring feature's public entrypoint for any shared type needed by Applications. [Tracker task](../../tracker/tasks/TASK-01M8AYCJG9Z3K4CF44B1GF4G5S-gate-optional-tailoring-provider-setup-by-availability.md)

1. Apply `errorToast: "local"` to the authenticated provider status GET. In the hook, classify its 404 as unsupported and other failures as failed. Expose one result with `loading`, `unsupported`, `failed`, and `loaded` states. Only the loaded state carries provider accounts. Clear actionable account state at the start of a retry and keep the existing generation check on all completions.
2. Pass the result and retry handler through `ApplicationDetailPage` to `ApplicationCvPanel`. Use the same result in Settings. Scope this state to the provider entry points. Keep the local coding-agent action and all existing session cards, including provider-origin draft review and recovery.
3. Render the states below. Keep provider readiness separate from the existing rule that a pending session or draft blocks a new run.

   | Provider lookup result | Application detail | Settings |
   | --- | --- | --- |
   | Loading | No provider actions | Loading status |
   | 404 unsupported | Omit optional provider entry points | Brief availability message |
   | Other lookup failure | One provider status error and Retry | One provider status error and Retry |
   | Loaded | Ready accounts can start when session rules permit. Show relevant setup links for accounts that need them | Show actions for the account status. Unavailable accounts have no connection or setup actions |

4. Keep Gemini's skill download and setup instructions inside the supported Gemini setup path. A positive ChatGPT status alone cannot expose Gemini setup. Retain the existing authorization URL validation and the status-driven connect, reconnect, check, and disconnect behavior.
5. Capture and remove OAuth callback parameters from the Settings URL promptly. Hold a valid payload only in memory while availability is unresolved. Submit a supported callback once, including through effect rerenders. On unsupported status, discard it and show a local message. A status Retry may resume an unsubmitted callback after a transient failure. Keep provider status retries separate from callback submissions already attempted.

**Pass criteria**

- Sign in through the production gateway with no provider routes. Application detail offers the coding-agent action and Settings shows availability without Retry or a skill download. Neither page shows a global provider error toast. An existing draft remains reachable.
- Intercept status with 503 then 200. Each affected surface shows one retryable message and renders the correct actions after retry. A late completion cannot restore obsolete availability.
- Cover `unavailable`, `disconnected`, `setup_required`, `ready`, and `reconnect` with fictional responses. Check both providers, and verify a ready account cannot start a second run while session rules block it.
- Use a synthetic OAuth callback to verify URL cleanup, zero callback POSTs on an unsupported deployment, and one POST on a supported deployment. Test transient status failure followed by retry while the callback is still pending.

## Finding 2 PDF import submission and progress

**Files** `web/src/features/cvs/components/import/ImportCvButton.tsx` and `web/src/features/cvs/components/import/ImportCvModal.tsx`. Reuse the existing CV store create call. [Tracker task](../../tracker/tasks/TASK-01M8AYCJG91RNFW55JDNWVR6EC-lock-pdf-import-and-show-progress-in-the-dialog.md)

1. Acquire an in-flight ref synchronously at the start of the parent submit handler, before reading credentials or starting any request. Ignore a second submission while held. The lock spans PDF parsing and CV creation. Release the lock and the pending React state in cleanup while retaining the existing key cleanup.
2. Pass the pending state to the modal. Display **Importing…** and announce it through a status element. Guard form submission and disable repeated activation, edits, and dismissal while pending. Use the synchronous lock for the parent's close guard, including Escape and backdrop clicks.
3. Keep a visible focus target while pending. For example, keep the submit button focusable with `aria-disabled` and retain both the form guard and the parent lock. When disabling a focused field moves focus out of the dialog, move it to the pending button. On failure, the same button becomes actionable again.
4. Keep the form mounted on parse or create failure, with its file, title, and template intact. One intentional retry starts one new attempt. On success, close and navigate once to the returned CV ID.

**Pass criteria**

- Hold `POST /api/v1/cvs/import/pdf` open in Chromium. Repeated clicks and Enter result in one parse request, visible progress, and no dismissal through Escape, backdrop, or Cancel.
- Finish parsing and hold `POST /api/v1/cvs` open. Repeating the interactions yields one create request. Release it and verify one navigation to the returned CV.
- Run parse failure and create failure separately. Verify all three form values survive, the modal becomes keyboard-operable again, and an intentional retry succeeds. Count requests at both stages.

## Finding 6 Accessible names and dialog focus

**Files** `web/src/features/cvs/components/CreateCvModal.tsx`, `web/src/features/cvs/components/import/ImportCvModal.tsx`, and `web/src/features/applications/components/ApplicationFormModal.tsx`. Reuse the existing `titleId` and `initialFocusRef` interface from `web/src/shared/ui/Modal.tsx`, as used by `ConfirmModal`. [Tracker task](../../tracker/tasks/TASK-01M8AYCJG9GY9T4C5D2J74CW32-name-cv-and-application-dialogs.md)

1. Generate a stable heading ID with `useId` in each caller. Assign it to the visible heading and pass it as `titleId`. The application form derives its name from the visible heading in each mode.
2. Generate a separate ID for the Create New CV title input and associate its label with `htmlFor`. Set the input as `initialFocusRef` and remove native `autoFocus` so the shared modal can record the opener before focusing the input.
3. Preserve dismissal and the first focus target on Import CV and both application modes when idle. Verify the new import pending state with its named dialog.

**Pass criteria**

- Locate the open dialogs by role and name **Create New CV**, **Import CV**, **Track an application**, and **Edit application**. Reopen them to verify name associations remain valid.
- Within Create New CV, locate the textbox named **Title** and check that it has initial focus. Escape returns focus to **+ New CV**.
- In each idle modal, forward and reverse Tab stay inside the dialog. Escape returns focus to the opener when it remains on the page.

## Checks and completion

Run the focused browser cases with a disposable database against the real web application where feasible. Intercept only the responses needed to reproduce status codes, slow network phases, and supported provider states. The repository's [fictional showcase fixtures](../../portfolio-showcase/README.md) provide sample inputs. If local application creation requires a missing model, use the deterministic extractor pattern in [api/tests/conftest.py](../../api/tests/conftest.py) for the disposable instance. Keep the real application, API client, and toast reporter in the expected-404 cases.

Run these commands from the repository root in a shell with the repository's dependencies set up. The existing browser harnesses and smoke script expect the POSIX `api/.venv/bin` layout. Use the established Linux or WSL environment for those commands when running on Windows.

```bash
(cd web && npm run lint && npm run typecheck)
(cd web && npm run architecture:test && npm run architecture:check)
./dev.sh --smoke
node web/scripts/test-tailoring-session.mjs
node web/scripts/test-tailoring-builder.mjs
git diff --check
```

Use the frontend build produced by the smoke run for builder browser checks. If smoke stops before it builds the web app, run `npm run build` from `web/` to enable the focused browser checks and record the smoke failure separately.

For each finding, record the test or command, the observed outcome, and any acceptance case that remains open. Update the corresponding tracker task after verification and run `tracker rebuild && tracker validate` with a compatible CLI. Preserve existing tracker history and report pre-existing warnings or tooling limits. A mocked provider response verifies frontend behavior. Production provider enablement requires its own end-to-end evidence.
