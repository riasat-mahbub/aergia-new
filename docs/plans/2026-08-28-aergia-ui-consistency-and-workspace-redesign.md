# Aergia UI consistency and workspace redesign

Tracker: `FEAT-01M14K1E63VC3EZ971AYEQETS5`

## Objective

Unify the application UI around the emerald/off-white visual direction,
separate the Dashboard, CV, Library, and Applications concepts, improve
application cards, expose all settings from one place, add favicon support,
and remove the password-change flow as requested.

This plan changes application chrome only. CV document content remains
HTML-first and user-customizable; changing the chrome palette must not silently
overwrite saved CV customizations.

## Delivery protocol

For every implementation step:

1. Search related tracker entries and inspect `tracker affects` results before
   editing.
2. Implement only that step.
3. Run the step's focused tests and static checks.
4. Commit the implementation with the step's commit message.
5. Run `tracker update FEAT-01M14K1E63VC3EZ971AYEQETS5 --status IN_PROGRESS
   --note "..."`.
6. Run `tracker rebuild && tracker validate`.
7. Commit the tracker update separately with a `tracker:` commit message.

Do not squash the implementation and tracker commits. Preserve unrelated user
changes if the worktree becomes dirty.

## Step 1 — Establish the application design system and asset hook

Commit: `ui: establish Aergia palette and shared surface styles`

Files in scope:

- `web/src/styles/tokens.css`
- `web/src/styles/tokens.ts`
- `web/src/index.css`
- `web/src/App.tsx`
- shared controls, modals, auth screens, CV cards, application screens, and
  builder chrome that currently use hard-coded blue/gray classes
- `web/index.html`
- `web/public/favicon.svg` or the agreed favicon asset path

Work:

- Replace the split proof-sheet/Library application styling with one semantic
  app token layer.
- Map the requested colors to canvas, surfaces, ink, primary, secondary/info,
  focus, and soft-accent roles.
- Keep red/amber semantic feedback roles and do not use status colors as
  arbitrary decoration.
- Use a darker derived primary for small white-on-color controls where needed;
  `#059669` alone does not provide sufficient contrast for all small white
  text.
- Migrate shared buttons, links, inputs, borders, cards, empty states, toasts,
  auth screens, builder chrome, and modal surfaces to semantic classes.
- Add favicon wiring in `web/index.html`. Use a replaceable SVG asset slot; a
  later brand asset replacement must not require component changes.
- Leave renderer-generated document styling and explicit per-CV accents intact.

Verification:

- `npm run lint`
- `npm run build`
- `npm run codegen:check`
- Source audit confirms no accidental application-wide blue primary remains.
- Existing customization and preview tests remain green.

## Step 2 — Reorganize the workspace and dashboard

Commit: `feat: reorganize dashboard around workspace domains`

Files in scope:

- `web/src/main.tsx`
- `web/src/components/common/AppLayout.tsx`
- `web/src/pages/CvListPage.tsx`
- new dashboard overview component/page as needed
- `web/src/pages/HomePage.tsx`
- builder, error, and not-found links that currently treat `/dashboard` as
  the CV list
- related route tests

Work:

- Make `/dashboard` an overview rather than a CV-only list.
- Add clear entry points and summaries for CVs, Library, and Applications.
- Add a dedicated CV route if needed, while keeping existing URLs usable
  during the transition.
- Remove the Library summary card from the CV-only surface.
- Remove the `Application CVs` grouping from the CV list. Do not delete or
  unlink generated CV records; application detail remains their owner and
  continues to provide Open/Edit and Export actions.
- Update navigation labels, active states, mobile wrapping, and all dashboard
  links consistently.

Verification:

- Update CV-list and routing tests for the new ownership model.
- Confirm ordinary CVs remain editable, copyable, and deletable.
- Confirm generated CVs remain reachable from their application.
- `npm run test -- --run` for affected frontend tests.

## Step 3 — Redesign Applications cards and detail surfaces

Commit: `ui: redesign application cards and detail surfaces`

Files in scope:

- `web/src/pages/ApplicationsPage.tsx`
- `web/src/pages/ApplicationDetailPage.tsx`
- shared card/status components if introduced
- application page tests

Work:

- Reuse the CV-card visual language: restrained surface, accent strip,
  consistent spacing, title hierarchy, and predictable action footer.
- Present company and role as the primary identity.
- Keep status, applied/updated dates, relevance, one-page fit, and generation
  state visible without making the card noisy.
- Replace the rainbow status palette with semantic statuses using the unified
  palette; retain a distinct danger treatment for rejected/delete states.
- Normalize link/button styling and make the generated-CV action the primary
  action when available.
- Keep status filtering, retry, delete, detail navigation, and generation
  behavior unchanged.

Verification:

- Update application page and detail tests for labels and action hierarchy.
- Test draft, ready, failed, rejected, and filtered states.
- `npm run test -- --run` for application tests.

## Step 4 — Consolidate Settings and LLM key management

Commit: `feat: consolidate account and import settings`

Files in scope:

- `web/src/components/common/AppLayout.tsx`
- `web/src/pages/SettingsPage.tsx`
- `web/src/components/cv-list/ImportCvButton.tsx`
- `web/src/components/builder/LLMKeyDialog.tsx`
- LLM/settings tests

Work:

- Keep one Settings entry in the global navigation.
- Move the LLM key trigger/status into the Settings page, with copy explaining
  that keys are in-memory only and cleared on import/logout/forget.
- Remove the second settings cog from the Import CV header.
- Keep Import CV focused on importing; preserve active-provider feedback in a
  non-settings form if it remains useful.
- Ensure LLM keys remain memory-only and are not moved into localStorage,
  cookies, URLs, Zustand persistence, or the backend account profile.

Verification:

- Update the Import CV test to assert the cog is gone and import still works.
- Add Settings coverage for opening, saving, forgetting, and closing LLM keys.
- Run the LLM key, settings, and import test groups.

## Step 5 — Remove the password-change flow

Commit: `security: remove password-change flow`

Files in scope:

- `web/src/pages/SettingsPage.tsx`
- `web/src/lib/store/authStore.ts`
- `api/app/routes/auth.py`
- `api/app/schemas/auth.py`
- `api/app/services/auth.py`
- `api/app/app.py` redaction list if obsolete fields remain
- `api/tests/test_auth.py`
- `api/tests/unit/test_schemas.py`
- frontend auth/settings tests

Work:

- Remove the Settings password form and all current/new/confirm password
  state and handlers.
- Remove the frontend `changePassword` store method.
- Remove the backend change-password route, request schema, and service method.
- Remove tests and imports that exist only for that endpoint.
- Do not replace it with a new-password-only form; that would weaken account
  security for a stolen authenticated session.
- Record the follow-up requirement for a proper email-based password reset
  flow with expiring, single-use tokens, rate limiting, and generic responses.

Verification:

- `rg` confirms no change-password endpoint, UI, or store method remains.
- Auth registration, login, refresh, logout, cookie, and redaction tests pass.
- No database migration is required because the password hash and refresh
  token fields remain part of authentication.

## Step 6 — Integration verification and closeout

Commit: `test: verify Aergia workspace redesign`

Run:

- `npm run test -- --run`
- `npm run lint`
- `npm run build`
- `npm run codegen:check`
- backend `pytest`
- backend `ruff check .`
- `./dev.sh --smoke` when the local Chromium/runtime prerequisites are
  available
- `tracker rebuild && tracker validate`

Check manually:

- Home, login, register, dashboard, CVs, Library, Applications, application
  detail, builder, and Settings use the same application chrome.
- Favicon resolves from the configured path.
- Generated application CVs still open and export.
- LLM keys remain ephemeral.
- The final feature tracker entry is updated to `DONE` with verification
  notes, then committed separately as a tracker commit.

## Follow-up outside this plan

- Add an email-based password recovery/reset flow before reintroducing account
  password changes.
- Replace the favicon SVG with the final branded asset when available.
