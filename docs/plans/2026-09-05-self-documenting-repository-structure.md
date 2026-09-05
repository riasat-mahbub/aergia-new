# Self-documenting repository structure implementation plan

**Date:** 2026-09-05  
**Status:** Planned  
**Tracker:** `TASK-01M1ST82B1EYQ1D1861A9RDEV2`  
**Baseline:** `master` at `d0f78fe` with a clean worktree  
**Supersedes:** The `web/src/app` ownership direction in
`2026-09-04-nextjs-readiness-handoff.md` and path assumptions in
`2026-09-04-frontend-boundary-solid-refactor.md`

**Reference conventions:** [TanStack Start routing](https://tanstack.com/start/latest/docs/framework/react/guide/routing),
[FastAPI documentation URLs](https://fastapi.tiangolo.com/tutorial/metadata/),
and [Codex `AGENTS.md` discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

## 1. Objective

Make the repository understandable from folder and file names before a
contributor reads detailed documentation.

The completed repository must have these properties:

1. TanStack Start route definitions live only in `web/src/routes/`.
2. Product capabilities live in `web/src/features/`.
3. Code used by several features lives in `web/src/shared/`.
4. `web/src/app/` does not exist.
5. The local tailoring skill, its portable contracts, tools, and tests live
   together in `tailoring-skill/`.
6. The backend document model and HTTP input/output models have distinct names.
7. Backend OpenAPI JSON and interactive Swagger documentation are available in
   development through the `/api` gateway.
8. The root `AGENTS.md` contains only repository-wide rules. Each main
   subsystem has its own `AGENTS.md` and README.
9. Product behavior, public URLs, API payloads, database shape, and the
   HTML-first rendering pipeline do not change.

## 2. Non-goals

Do not include any of the following work:

- Do not migrate to Next.js.
- Do not change TanStack Start, TanStack Router, Vite, or Nitro versions.
- Do not redesign the frontend test suite. That work is deferred.
- Do not reorganize the existing backend tests by test type.
- Do not add editor-specific settings.
- Do not change database tables or create an Alembic migration.
- Do not change the tailoring protocol version.
- Do not change the public `/agent/tailor/$sessionId` URL.
- Do not change `/api/v1/*` application endpoint URLs.
- Do not rewrite components, stores, or services while moving them.
- Do not create a large repository-map document. Folder names and local
  READMEs are the primary navigation system.
- Do not hand-edit `web/src/generated/schema.ts` or
  `web/src/routeTree.gen.ts`.

## 3. Safety rules for the implementing model

Follow these rules during every phase:

1. Start only from a clean worktree. If `git status --short` is not empty,
   stop and resolve ownership of those changes before continuing.
2. Read the root `AGENTS.md`, the relevant local `AGENTS.md`, and related
   tracker entries before editing each subsystem.
3. Use `git mv` for tracked file moves. This preserves history.
4. Make mechanical moves first. Make behavior changes only when a route must
   pass a URL value into a feature page.
5. Do not rename exported functions, API types, store actions, or CSS classes
   unless this plan names the rename.
6. Update imports immediately after each move. Do not leave temporary
   compatibility re-export files unless this plan explicitly requests one.
7. Run the phase verification before starting the next phase.
8. If a phase fails, repair that phase. Do not continue with known failures.
9. Commit only after the relevant verification passes. Phases 3 and 4 must use
   one commit per feature so failures and reverts stay small. The final branch
   must merge into `master` with a regular merge commit.
10. Use `rg` to prove that old paths are gone. Do not assume an IDE moved all
    imports.

## 4. Architecture decisions

### 4.1 Frontend ownership

Use this dependency direction:

```text
routes
  -> feature public entry points
  -> shared modules

features
  -> their own private modules
  -> other feature public entry points when required
  -> shared modules

shared
  -> other shared modules
  -X-> features
  -X-> routes
```

The terms have these exact meanings:

- `routes/` maps URLs to components. It owns route registration, URL
  parameters, search validation, redirects, route context, SSR settings,
  pending components, and route layouts.
- `features/` owns a product capability. A feature may contain pages,
  components, hooks, state, API operations, types, and pure domain logic.
- `shared/` owns reusable technical or CV-editor building blocks used by two
  or more features.
- `generated/` owns generated source. Other code imports generated CV types
  through the shared CV schema facade.
- `middleware/` owns TanStack Start request middleware.

Do not add a top-level `pages/` directory. A page is part of a feature. Use a
feature-local `pages/` directory only when one feature has multiple routed
screens, such as Authentication or Applications.

### 4.2 Route and feature coupling

Route files must import features through a feature `index.ts` file:

```ts
import { BuilderPage } from "@/features/builder";
```

Do not use a deep route-to-feature import such as:

```ts
import BuilderPage from "@/features/builder/pages/BuilderPage";
```

Route files must read inbound URL data and pass plain props to page
components. This applies to:

- Builder `id` and optional `application` search value.
- Application Detail `id`.
- Library optional `kind` search value.
- Public tailoring `sessionId`.

Feature UI may continue to use TanStack `Link`, `useNavigate`, and
`useBlocker` for outbound navigation and unsaved-change behavior. Do not add a
navigation abstraction only to remove these imports. Features must never
import files from `src/routes/` or `routeTree.gen.ts`.

Route layout files must render `Outlet`. Visual layout components receive
`children` and must not import `Outlet` themselves.

### 4.3 Feature public APIs

Every feature must have an `index.ts` file. Export only items used by routes
or other features. Internal components must use relative imports.

Cross-feature imports must target the public entry point:

```ts
import { useApplicationStore } from "@/features/applications";
```

Do not use:

```ts
import { useApplicationStore } from "@/features/applications/state/applicationStore";
```

### 4.4 Backend model names

Rename the two similar backend packages:

```text
api/app/schema/   -> api/app/document_schema/
api/app/schemas/  -> api/app/http_schemas/
```

`document_schema` is the source of truth for the CV AST, template manifest,
renderer input, and renderer output. `http_schemas` contains endpoint request
and response models.

### 4.5 OpenAPI scope

FastAPI remains the OpenAPI source of truth. Do not commit a generated
`openapi.json` snapshot in this change.

Development and test environments expose:

```text
/api/docs
/api/openapi.json
```

Production disables both routes by default. ReDoc is not required for this
change. Swagger UI is sufficient and avoids a second documentation asset set.

## 5. Final repository shape

The important final directories must look like this:

```text
aergia/
  AGENTS.md
  README.md
  DEPLOY.md
  api/
    AGENTS.md
    README.md
    app/
      document_schema/
      http_schemas/
      core/
      db/
      models/
      routes/
      services/
    alembic/
    scripts/
    tests/
  web/
    AGENTS.md
    README.md
    scripts/
    server/
    src/
      routes/
      features/
      shared/
      generated/
      middleware/
      styles/
      router.tsx
      routeTree.gen.ts
      start.ts
  tailoring-skill/
    AGENTS.md
    README.md
    THIRD_PARTY_NOTICES.md
    skills/
      aergia-tailor/
        SKILL.md
    contracts/
      evidence-packet.schema.json
      tailoring-patch.schema.json
      fixtures/
    tools/
    tests/
  docs/
    plans/
  scripts/
  tracker/
  tracker-legacy/
```

The final `web/src` ownership tree must be:

```text
web/src/
  routes/
  features/
    app-shell/
    applications/
    authentication/
    builder/
    cvs/
    dashboard/
    home/
    library/
    llm-credentials/
    profile/
    settings/
    tailoring/
    templates/
  shared/
    api/
    browser/
    cv/
    cv-editor/
    forms/
    rich-text/
    security/
    state/
    ui/
  generated/
  middleware/
  styles/
```

## 6. Implementation phases

### Phase 0: Preflight and decision record

1. Confirm the baseline:

   ```bash
   git branch --show-current
   git rev-parse --short HEAD
   git status --short
   tracker validate
   ```

2. Confirm the branch is based on `master` and the worktree is clean.
3. Create the feature branch `refactor/self-documenting-repository`.
4. Read these existing records:

   - `FEAT-01M1PQEVJTWRNXWRWEGMB7NMVT`
   - `FEAT-01M1QRT0VH26RTPBDYSYQ8WQXT`
   - `TASK-01M1PT0PPNNTES6JFD3KS60Q2M`
   - `FEAT-01M1G4FG0YGJB1XWBMDGV0PDTM`
   - `docs/plans/2026-09-04-nextjs-readiness-handoff.md`
   - `docs/plans/2026-09-04-frontend-boundary-solid-refactor.md`

5. Create an ADR named `Organize the TanStack frontend by routes, features,
   and shared modules`. Record these decisions:

   - TanStack Start is the current target framework.
   - `src/routes` is the route source of truth.
   - `src/app` is removed.
   - A future Next.js migration must create a new ADR and plan.
   - Feature folders own their UI and behavior.

6. Link the ADR and this task in the tracker.
7. Mark both older frontend plan documents as superseded. Do not delete them.
8. Run `tracker rebuild && tracker validate`.

**Phase 0 commit:**

```text
docs: record routes-features-shared frontend direction
```

### Phase 1: Make the boundary checker support the target structure

Update:

- `web/scripts/check-frontend-boundaries.mjs`
- `web/scripts/check-frontend-boundaries-fixtures.mjs`

Implement these rules:

1. A file under `shared/` cannot import `features/` or `routes/`.
2. A file under `features/` cannot import `routes/` or
   `routeTree.gen.ts`.
3. A route can import a feature only through
   `features/<feature>/index.ts`.
4. A feature can import another feature only through that feature's
   `index.ts`.
5. A feature's internal files are private to that feature.
6. Files under a `domain/` directory cannot import React, Zustand, Axios,
   browser globals, `api/`, `state/`, `components/`, or `pages/`.
7. Files under an `api/` directory cannot import feature components, pages,
   hooks, or state.
8. Files under a `state/` directory cannot import feature components or pages.
9. Only `shared/api/client.ts` may create or configure the Axios client.
10. `web/src/generated/schema.ts` may be imported only by
    `web/src/shared/cv/schema.ts`.

During Phases 1 through 4, keep the existing `app/` privacy checks so the
repository can remain green while files move. Do not add the final
"`src/app` is forbidden" assertion until Phase 5.

Add fixture cases for every rule. Include at least one passing fixture that
shows a route importing a feature public API and one passing fixture that
shows a feature importing another feature public API.

Run:

```bash
cd web
npm run architecture:test
npm run architecture:check
npm run lint -- --quiet
npm run build
```

**Phase 1 commit:**

```text
refactor(web): teach boundary checks the feature architecture
```

### Phase 2: Move reusable frontend code into `shared`

Perform these moves without changing behavior:

| Current path | Target path |
|---|---|
| `web/src/services/client.ts` | `web/src/shared/api/client.ts` |
| `web/src/lib/browser/` | `web/src/shared/browser/` |
| `web/src/lib/cv/` | `web/src/shared/cv/` |
| `web/src/lib/forms/` | `web/src/shared/forms/` |
| `web/src/lib/rich-text/` | `web/src/shared/rich-text/` |
| `web/src/lib/security/` | `web/src/shared/security/` |
| `web/src/components/common/section-editors/` | `web/src/shared/cv-editor/` |
| generic files in `web/src/components/common/` | `web/src/shared/ui/` |
| `web/src/store/uiStore.ts` | `web/src/shared/state/uiStore.ts` |

Generic files are:

- `AccordionPanel.tsx`
- `DateField.tsx`
- `EmptyState.tsx`
- `LoadingSkeleton.tsx`
- `Modal.tsx`
- `SortableAccordionList.tsx`
- `Toast.tsx`

Keep `web/src/generated/`, `web/src/middleware/`, and `web/src/styles/` in
place.

After the moves:

1. Update all imports from `@/services/client` to `@/shared/api/client`.
2. Update all `@/lib/cv/*` imports to `@/shared/cv/*`.
3. Update the remaining moved imports in the same way.
4. Update relative imports inside the moved editor tree.
5. Preserve the generated-schema facade in `shared/cv/schema.ts`.
6. Do not import `generated/schema.ts` directly anywhere else.
7. Remove empty legacy directories only after `rg` confirms no imports use
   them.

Proof commands:

```bash
rg -n '@/services/client|@/lib/(browser|cv|forms|rich-text|security)|@/components/common|@/store/uiStore' web/src
rg -n '@/generated/schema' web/src --glob '!generated/schema.ts' --glob '!shared/cv/schema.ts'
```

Both commands must return no unexpected matches.

Run the full frontend verification block from Phase 1 and
`npm run codegen:check`.

**Phase 2 commit:**

```text
refactor(web): group reusable code under shared
```

### Phase 3: Create non-route feature foundations

Move shared business capability code before moving page UI. Create an
`index.ts` public API for every target feature.

#### Authentication

```text
web/src/contracts/auth.ts
  -> web/src/features/authentication/types/index.ts
web/src/services/auth.ts
  -> web/src/features/authentication/api/auth.ts
web/src/services/session.functions.ts
  -> web/src/features/authentication/api/session.functions.ts
web/src/store/authStore.tsx
  -> web/src/features/authentication/state/authStore.tsx
web/src/lib/validators/auth.ts
  -> web/src/features/authentication/domain/validators.ts
```

#### Applications

```text
web/src/contracts/applications.ts
  -> web/src/features/applications/types/index.ts
web/src/services/applications.ts
  -> web/src/features/applications/api/applications.ts
web/src/app/dashboard/_stores/applicationStore.ts
  -> web/src/features/applications/state/applicationStore.ts
web/src/app/dashboard/_constants/applicationStatus.ts
  -> web/src/features/applications/domain/status.ts
```

#### CVs

```text
web/src/contracts/cvs.ts
  -> web/src/features/cvs/types/index.ts
web/src/services/cvs.ts
  -> web/src/features/cvs/api/cvs.ts
web/src/app/dashboard/_stores/cvListStore.ts
  -> web/src/features/cvs/state/cvListStore.ts
```

#### Library

```text
web/src/contracts/library.ts
  -> web/src/features/library/types/index.ts
web/src/services/library.ts
  -> web/src/features/library/api/library.ts
web/src/store/libraryStore.ts
  -> web/src/features/library/state/libraryStore.ts
web/src/lib/library/catalog.ts
  -> web/src/features/library/domain/catalog.ts
web/src/components/library/LibraryEntryCard.tsx
  -> web/src/features/library/components/LibraryEntryCard.tsx
```

#### LLM credentials

```text
web/src/contracts/llm.ts
  -> web/src/features/llm-credentials/types/index.ts
web/src/store/llmKeyStore.ts
  -> web/src/features/llm-credentials/state/llmKeyStore.ts
web/src/lib/llm/providers.ts
  -> web/src/features/llm-credentials/domain/providers.ts
```

Keep the memory-only credential behavior unchanged.

#### Templates

```text
web/src/contracts/templates.ts
  -> web/src/features/templates/types/index.ts
web/src/services/templates.ts
  -> web/src/features/templates/api/templates.ts
```

#### Profile

```text
web/src/app/dashboard/_components/profile/UserProfileEditor.tsx
  -> web/src/features/profile/components/UserProfileEditor.tsx
web/src/app/dashboard/_services/profile.ts
  -> web/src/features/profile/api/profile.ts
web/src/app/dashboard/_stores/profileStore.ts
  -> web/src/features/profile/state/profileStore.ts
web/src/app/dashboard/_types/profile.ts
  -> web/src/features/profile/types/index.ts
```

For each feature:

1. Use relative imports inside the feature.
2. Export externally used symbols from `index.ts`.
3. Update all consumers to import from the public feature entry point.
4. Do not add wildcard exports. List each public symbol explicitly.
5. Do not merge or rename types while moving them.

After all moves, these directories should be empty and removable:

```text
web/src/contracts/
web/src/services/
web/src/store/
web/src/lib/
web/src/components/
```

Do not remove `web/src/app/` yet. It still contains page UI.

Run the frontend verification block and `npm run codegen:check`.

**Phase 3 commits:**

```text
refactor(web): create the authentication feature foundation
refactor(web): create the applications feature foundation
refactor(web): create the CV feature foundation
refactor(web): create the library feature foundation
refactor(web): create the LLM credentials feature foundation
refactor(web): create the templates feature foundation
refactor(web): create the profile feature foundation
```

### Phase 4: Move page UI into features

Move one feature at a time. Run at least `npm run typecheck` and
`npm run architecture:check` after each feature. Run the full frontend block
after all feature moves.

#### App shell

Move:

```text
web/src/app/layout.tsx
  -> web/src/features/app-shell/RootLayout.tsx
web/src/app/error.tsx
  -> web/src/features/app-shell/ErrorPage.tsx
web/src/app/loading.tsx
  -> web/src/features/app-shell/LoadingPage.tsx
web/src/app/not-found.tsx
  -> web/src/features/app-shell/NotFoundPage.tsx
web/src/app/_providers/ClientProviders.tsx
  -> web/src/features/app-shell/ClientProviders.tsx
```

Change `RootLayout` to accept `children: ReactNode`. Remove its direct
`Outlet` import. Export the shell components from
`features/app-shell/index.ts`.

#### Home

```text
web/src/app/page.tsx
  -> web/src/features/home/HomePage.tsx
```

#### Authentication pages

```text
web/src/app/login/page.tsx
  -> web/src/features/authentication/pages/LoginPage.tsx
web/src/app/login/_components/LoginForm.tsx
  -> web/src/features/authentication/components/LoginForm.tsx
web/src/app/register/page.tsx
  -> web/src/features/authentication/pages/RegisterPage.tsx
web/src/app/register/_components/RegisterForm.tsx
  -> web/src/features/authentication/components/RegisterForm.tsx
web/src/app/register/_components/TurnstileWidget.tsx
  -> web/src/features/authentication/components/TurnstileWidget.tsx
```

#### Applications pages

Move `web/src/app/dashboard/applications/` into
`web/src/features/applications/` using these names:

```text
page.tsx                         -> pages/ApplicationListPage.tsx
[id]/page.tsx                    -> pages/ApplicationDetailPage.tsx
_components/                     -> components/
[id]/_components/                -> components/detail/
_lib/                            -> domain/list/
[id]/_lib/applicationDetail.ts   -> domain/detail/applicationDetail.ts
```

Move tailoring-session-specific files out of Application Detail:

```text
[id]/_hooks/useTailoringSession.ts
  -> features/tailoring/hooks/useTailoringSession.ts
[id]/_hooks/useLinkedCv.ts
  -> features/applications/hooks/useLinkedCv.ts
[id]/_lib/tailoringPresentation.ts
  -> features/tailoring/domain/tailoringPresentation.ts
[id]/_services/tailoring.ts
  -> features/tailoring/api/tailoring.ts
[id]/_types/tailoring.ts
  -> features/tailoring/types/index.ts
```

Keep application-detail-only components in Applications. Import the public
Tailoring API where needed.

#### Public tailoring page

```text
web/src/app/agent/tailor/[sessionId]/page.tsx
  -> web/src/features/tailoring/pages/TailoringSessionPage.tsx
```

The route reads `sessionId` and passes it as a prop. The feature page must not
call `useParams`.

#### CV list

Move `web/src/app/dashboard/cvs/` into `web/src/features/cvs/`:

```text
page.tsx       -> pages/CvListPage.tsx
_components/   -> components/
_services/     -> api/
_types/imports.ts -> types/imports.ts
```

Keep the existing CV contracts in `features/cvs/types/index.ts`. Keep the
import-specific types in `features/cvs/types/imports.ts`. Export the required
types from the feature's public `index.ts`.

#### Library page

Move `web/src/app/dashboard/library/` into `web/src/features/library/`:

```text
page.tsx         -> pages/LibraryPage.tsx
_components/     -> components/
_lib/             -> domain/
```

The route reads the optional `kind` search value and passes
`initialKind?: string` to the page. The feature page must not call
`useSearch`.

#### Settings

Move:

```text
web/src/app/dashboard/settings/page.tsx
  -> web/src/features/settings/SettingsPage.tsx
web/src/app/dashboard/settings/_components/
  -> web/src/features/settings/components/
```

Settings imports Profile and LLM Credentials through their public feature
entry points.

#### Builder

Move `web/src/app/builder/[id]/` to `web/src/features/builder/`:

```text
page.tsx       -> BuilderPage.tsx
_components/   -> components/
_hooks/        -> hooks/
_lib/          -> domain/
_services/     -> api/
_stores/       -> state/
_types/        -> types/
```

Change `BuilderPage` to accept:

```ts
interface BuilderPageProps {
  cvId: string;
  applicationId: string | null;
}
```

Remove `useParams` and `useSearch` from `BuilderPage`. Preserve
`useNavigate` and `useUnsavedChanges` behavior. Rename local variable `id` to
`cvId` only where needed to accept the prop; do not change API payload names.

#### Dashboard

Move last because it consumes several feature public APIs:

```text
web/src/app/dashboard/layout.tsx
  -> web/src/features/dashboard/DashboardLayout.tsx
web/src/app/dashboard/page.tsx
  -> web/src/features/dashboard/DashboardPage.tsx
web/src/app/dashboard/_components/ApplicationRow.tsx
  -> web/src/features/dashboard/components/ApplicationRow.tsx
web/src/app/dashboard/_components/SummaryCard.tsx
  -> web/src/features/dashboard/components/SummaryCard.tsx
web/src/app/dashboard/_lib/dashboardPresentation.ts
  -> web/src/features/dashboard/domain/dashboardPresentation.ts
```

Change `DashboardLayout` to accept `children: ReactNode`. Remove its direct
`Outlet` import. It may retain TanStack links and navigation hooks.

After every move:

- Rename underscore-prefixed implementation folders to normal names. The
  underscore convention belongs to a route tree, not a feature tree.
- Add or update the feature `index.ts`.
- Update route imports immediately.
- Keep every current route path and SSR setting unchanged.

**Phase 4 commits:**

```text
refactor(web): move the app shell into its feature
refactor(web): move the home page into its feature
refactor(web): move authentication pages into their feature
refactor(web): move application pages into their feature
refactor(web): move the tailoring page into its feature
refactor(web): move the CV list into its feature
refactor(web): move the Library page into its feature
refactor(web): move Settings into its feature
refactor(web): move Builder into its feature
refactor(web): move Dashboard into its feature
```

### Phase 5: Make routes the only route tree and remove legacy frontend paths

Update route adapters as follows.

#### Root route

`web/src/routes/__root.tsx` continues to own:

- `createRootRouteWithContext`
- session resolution
- document `<html>`, `<head>`, and `<body>`
- `HeadContent` and `Scripts`
- route pending and not-found components

It imports Auth and App Shell through public feature entry points. It renders
`Outlet` inside `RootLayout`:

```tsx
<RootLayout>
  <Outlet />
</RootLayout>
```

#### Dashboard and Builder layouts

Both route layout files render:

```tsx
<DashboardLayout>
  <Outlet />
</DashboardLayout>
```

The visual `DashboardLayout` does not import `Outlet`.

#### Inbound route props

Use named wrapper components in route files:

```tsx
function BuilderRoute() {
  const { id } = Route.useParams();
  const { application } = Route.useSearch();
  return <BuilderPage cvId={id} applicationId={application ?? null} />;
}
```

Apply the same pattern to Application Detail, Library, and the public
Tailoring Session page.

Do not change the route filenames. TanStack file-based routing must remain in
`src/routes`. Do not hand-edit `routeTree.gen.ts`; run the normal build to
regenerate it if required.

After the adapters work:

1. Remove `web/src/app/`.
2. Add a boundary-check failure for any source file under `web/src/app/`.
3. Remove transitional old-architecture logic from the checker.
4. Confirm that top-level `components`, `contracts`, `lib`, `services`, and
   `store` directories are absent.

Proof commands:

```bash
test ! -d web/src/app
test ! -d web/src/components
test ! -d web/src/contracts
test ! -d web/src/lib
test ! -d web/src/services
test ! -d web/src/store
rg -n '@/app/|@/components/|@/contracts/|@/lib/|@/services/|@/store/' web/src web/scripts
rg -n 'useParams|useSearch' web/src/features
```

The final `rg` command may report a justified feature use only if it is not
one of the four inbound route values listed in this plan. Review every match.

Run:

```bash
cd web
npm run architecture:test
npm run architecture:check
npm run lint
npm run typecheck
npm run codegen:check
npm run build
```

Confirm all existing URLs are unchanged by inspecting the generated route
tree diff.

**Phase 5 commit:**

```text
refactor(web): make TanStack routes the only route tree
```

### Phase 6: Package the tailoring skill and contracts together

Use `git mv` for these moves:

```text
agent/                         -> tailoring-skill/
contracts/                     -> tailoring-skill/contracts/
tailoring-skill/test/          -> tailoring-skill/tests/
```

Preserve this nested path exactly:

```text
tailoring-skill/skills/aergia-tailor/SKILL.md
```

Update:

- `tailoring-skill/README.md`
- root `README.md`
- root and local `AGENTS.md` files
- `api/tests/test_tailoring_contracts.py`
- any scripts or documentation found by the proof search

Change the backend fixture path from root `contracts/fixtures` to
`tailoring-skill/contracts/fixtures`.

Do not change:

- JSON Schema `$id` values. They identify protocol documents and are not file
  paths.
- `protocol_version`.
- API endpoint paths.
- Browser route `/agent/tailor/$sessionId`.
- Class and operation names in the tailoring protocol.

Proof command:

```bash
rg -n '(^|[^-])agent/|(^|[^-])contracts/' . \
  --glob '!tracker/**' \
  --glob '!tracker-legacy/**' \
  --glob '!api/.venv/**' \
  --glob '!web/node_modules/**' \
  --glob '!web/.output/**' \
  --glob '!web/dist/**'
```

Review every result. Protocol URLs containing `/agent/tailor/` and stable
JSON Schema `$id` values are expected. Old repository file paths are not.

Run:

```bash
node --test tailoring-skill/tests/*.test.mjs
cd api
.venv/bin/pytest tests/test_tailoring_contracts.py tests/test_tailoring.py
```

**Phase 6 commit:**

```text
refactor: package the tailoring skill with its contracts
```

### Phase 7: Disambiguate backend schema packages

Use:

```text
api/app/schema/   -> api/app/document_schema/
api/app/schemas/  -> api/app/http_schemas/
```

Update every Python import and every documentation reference:

```text
app.schema.models       -> app.document_schema.models
app.schema              -> app.document_schema
app.schemas.<domain>    -> app.http_schemas.<domain>
```

Update `api/scripts/codegen_schema.py`:

```text
SOURCE_MODULE = "app.document_schema.models"
SOURCE_PATH = REPO_ROOT / "api" / "app" / "document_schema" / "models.py"
```

Update its module docstring and generated source comment.

Run code generation. The generated TypeScript model declarations must not
change. The expected generated diff is only the source-path header comment:

```text
api/app/schema/models.py
  -> api/app/document_schema/models.py
```

If generated interfaces or type aliases change, stop and investigate. A
package rename must not change the wire schema.

Proof commands:

```bash
rg -n 'app\.schema|app\.schemas|api/app/schema|api/app/schemas' api web README.md DEPLOY.md docs AGENTS.md
test ! -d api/app/schema
test ! -d api/app/schemas
```

Run:

```bash
cd api
.venv/bin/ruff check .
.venv/bin/pytest tests/test_schema.py tests/test_codegen.py tests/test_sections.py tests/test_resolve.py tests/test_tailoring_contracts.py
cd ../web
npm run codegen
npm run codegen:check
npm run typecheck
npm run build
```

**Phase 7 commit:**

```text
refactor(api): distinguish document and HTTP schemas
```

### Phase 8: Add development OpenAPI exploration

#### Settings

Add a read-only computed setting or helper with this behavior:

```text
development -> API docs enabled
test        -> API docs enabled
production  -> API docs disabled
```

Do not add an enabled-by-default production override in this change.

#### FastAPI URLs

Configure the existing `FastAPI` instance:

```python
app = FastAPI(
    ...,
    docs_url="/api/docs" if api_docs_enabled else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if api_docs_enabled else None,
)
```

The `/api` prefix is required because both Vite and the production TanStack
gateway proxy `/api/*` to FastAPI.

#### Tags

Add ordered OpenAPI tag metadata for:

```text
auth
cvs
applications
profile
library
assets
templates
render
imports
tailoring
system
```

Assign exactly one primary tag to every application operation. Prefer tags on
`include_router` calls so all operations in a mounted router receive the same
tag. Remove duplicate router-level tags from `render` and `imports` if this
would otherwise produce two identical or competing tags.

Tag `/healthz` and `/readyz` as `system`.

#### Security headers and Swagger assets

FastAPI's default Swagger UI loads JavaScript and CSS from
`https://cdn.jsdelivr.net`. The current development CSP does not allow that
host. Make the smallest development-only CSP change that lets `/api/docs`
load.

Requirements:

1. Production CSP must not become less strict.
2. Swagger must remain disabled in production.
3. Do not add `unsafe-inline` to production.
4. Prefer a docs-path-specific development policy. If the existing middleware
   design makes that impractical, allow `https://cdn.jsdelivr.net` only in the
   development policy.
5. Test the page through the public development origin, not only port 8000.

For a path-specific policy, pass `request.url.path` into the CSP builder from
`_apply_security_headers`. Add the CDN host only when the path is `/api/docs`
and the environment is not production. The existing development policy
already permits the inline script used by Swagger. Do not change the
production branch.

#### OpenAPI checks

Add a focused backend test that asserts:

- `app.openapi()` reports OpenAPI 3.1.
- all `/api/v1/*` operations have one primary tag;
- `/api/docs` and `/api/openapi.json` are configured outside production;
- the schema has no duplicate operation IDs;
- key paths such as auth, CVs, render, and tailoring are present.

Do not build a new general test framework for this test.

Run the development servers and verify:

```text
http://localhost:5173/api/docs
http://localhost:5173/api/openapi.json
```

Verify that the browser console has no CSP errors for Swagger assets. Confirm
that authenticated write requests still require the existing cookie and CSRF
rules. Do not weaken CSRF to make Swagger mutations easier.

Run:

```bash
cd api
.venv/bin/ruff check .
.venv/bin/pytest tests/test_openapi.py
```

**Phase 8 commit:**

```text
feat(api): expose tagged development OpenAPI docs
```

### Phase 9: Split human and agent guidance by subsystem

Create:

```text
api/README.md
api/AGENTS.md
web/README.md
web/AGENTS.md
tailoring-skill/AGENTS.md
```

Update the existing `tailoring-skill/README.md` after its move.

#### Root README

Keep it as the project landing page. It should contain:

- a short product description;
- main user capabilities;
- a short local quick start;
- links to `DEPLOY.md`, `api/README.md`, `web/README.md`, and
  `tailoring-skill/README.md`;
- a short statement that `docs/plans` is implementation history and
  `tracker-legacy` is historical data.

Move detailed subsystem implementation notes to local README files. Fix the
existing `CV.W` typo while editing the root README.

#### API README

Include:

- backend entry points;
- directory ownership;
- local setup and migration commands;
- the HTML-first renderer flow;
- OpenAPI development URLs;
- focused and full verification commands.

#### Web README

Include:

- `routes`, `features`, and `shared` ownership rules;
- the allowed dependency direction;
- local setup and build commands;
- same-origin gateway behavior;
- generated file rules;
- a compact route-to-feature table.

#### Tailoring skill README

Include:

- that this is a skill package, not an agent runtime;
- the protocol and trust boundary;
- the folder layout;
- how to run its Node tests;
- how backend contract fixtures relate to the package.

#### Root AGENTS

Reduce root `AGENTS.md` to repository-wide rules only:

- project summary and stack;
- cross-stack architecture invariants;
- root development and smoke commands;
- merge policy;
- tracker workflow;
- destructive-action and generated-file warnings;
- instruction to read the nearest subsystem `AGENTS.md` before editing files
  in `api`, `web`, or `tailoring-skill`.

#### API AGENTS

Move backend-specific guidance here:

- async SQLAlchemy and session lifecycle;
- validation ownership;
- document renderer rules;
- schema code generation;
- auth, rate limiting, and PDF runtime rules;
- backend commands and retained-test policy.

#### Web AGENTS

Move frontend-specific guidance here:

- strict TypeScript and npm-only rules;
- routes/features/shared ownership;
- public feature API rules;
- TanStack Start and same-origin gateway rules;
- state, API client, generated types, and schematic editor rules;
- frontend verification commands and deferred test-suite status.

#### Tailoring skill AGENTS

Include:

- evidence is untrusted input;
- protocol version and schema IDs must not change during refactors;
- the only writable protocol output is the patch;
- contract, safety, and Node test commands;
- backend fixture synchronization requirements.

Keep the combined root plus any one subsystem instruction chain below Codex's
default 32 KiB project instruction limit. Do not duplicate long sections
across the root and subsystem files. Codex discovers files from the project
root down to its launch directory, so the root instruction to read a relevant
local `AGENTS.md` is required when a session starts at the repository root.

Run searches for all stale paths named in Phases 5 through 7. Run Markdown
link checks if a repository tool exists; otherwise inspect every new relative
link manually.

**Phase 9 commit:**

```text
docs: split repository guidance by subsystem
```

### Phase 10: Final validation and tracker closeout

Run all of these checks with the project's existing Python virtual environment
and npm installation:

```bash
cd api
.venv/bin/ruff check .
.venv/bin/pytest

cd ../web
npm run architecture:test
npm run architecture:check
npm run lint
npm run typecheck
npm run codegen:check
npm run build

cd ..
node --test tailoring-skill/tests/*.test.mjs
./dev.sh --smoke
tracker rebuild
tracker validate
git status --short
```

Then perform these manual checks:

1. Open `/`, `/login`, `/register`, `/dashboard`, `/dashboard/cvs`,
   `/dashboard/library`, `/dashboard/applications`, an application detail
   route, `/builder/:id`, `/dashboard/settings`, and
   `/agent/tailor/:sessionId`.
2. Confirm unauthenticated protected routes still redirect to `/login`.
3. Confirm Builder loading, editing, save, preview, and export still work.
4. Confirm Library add, edit, delete, and Builder insertion still work.
5. Confirm the public tailoring landing page does not fetch session evidence.
6. Open `/api/docs` and verify all operation groups.
7. Fetch `/api/openapi.json` through the public development origin.
8. Start with `ENVIRONMENT=production` and confirm `/api/docs` and
   `/api/openapi.json` return 404.
9. Inspect the Git diff for accidental route, payload, generated type, or
   database changes.

Update `TASK-01M1ST82B1EYQ1D1861A9RDEV2` to `DONE` with the final verification
results. Update or supersede any related in-progress tracker record whose old
path assumptions are no longer true. Rebuild and validate the tracker again.

Merge the feature branch into `master` with a regular merge commit. Do not
squash the phase commits.

## 7. Verification matrix

| Change | Required proof |
|---|---|
| Shared frontend moves | architecture tests, lint, typecheck, build |
| Each feature move | typecheck and architecture check |
| Final frontend tree | full frontend checks and unchanged route URLs |
| Tailoring package move | Node tests and focused backend tailoring tests |
| Backend schema rename | Ruff, schema/codegen tests, unchanged generated types |
| OpenAPI docs | focused test, live Swagger page, live JSON, production 404 |
| Guidance split | stale-path search and link review |
| Full change | backend pytest, frontend checks, tailoring tests, smoke gate |

## 8. Stop conditions

Stop implementation and investigate if any of these conditions occurs:

- A generated TypeScript interface changes during the backend package rename.
- A TanStack route path changes.
- A tailoring JSON Schema `$id` or protocol version changes.
- An Alembic migration appears in the diff.
- A component move requires a product behavior rewrite.
- A feature and `shared` import each other.
- Two features import each other's internal files.
- Swagger requires weaker production CSP or weaker CSRF rules.
- The implementation requires restoring the removed frontend test framework.
- The worktree contains unrelated user changes.

## 9. Completion criteria

The work is complete only when all statements are true:

- `web/src/routes` is the only URL tree.
- `web/src/features` owns all product pages and feature behavior.
- `web/src/shared` owns all cross-feature frontend code.
- Old frontend layer directories are absent.
- Boundary checks enforce the new dependency direction.
- `tailoring-skill` contains its skill, contracts, tools, and tests.
- `document_schema` and `http_schemas` replace the ambiguous backend names.
- OpenAPI is grouped, reachable in development, and disabled in production.
- Root and subsystem README and AGENTS files have distinct roles.
- All automated and manual checks in Phase 10 pass.
- The tracker is rebuilt, valid, and updated.
