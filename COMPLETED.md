# Aergia CV Builder — Completed Plans Archive

This file contains all historically completed development phases. Moved from PLAN.md on 2026-06-27 to make room for the new manifest-based template system roadmap.

---

## Phase 1 — Foundation (Auth) ✅

| # | Task | Status |
|---|------|--------|
| 1 | Set up docker-compose.yml with Postgres service | ✅ |
| 2 | Initialize FastAPI project (main.py, config, models, schemas) | ✅ |
| 3 | Implement users model + table migration | ✅ |
| 4 | Auth: register, login, refresh, logout, change-password | ✅ |
| 5 | Initialize React + TS + Vite + Tailwind project | ✅ |
| 6 | Login + register pages with forms (HookForm + Zod) | ✅ |
| 7 | Zustand authStore + JWT token management | ✅ |
| 8 | Axios interceptor for Bearer token | ✅ |
| 9 | Protected routes (redirect to login if unauthenticated) | ✅ |
| T1 | Pytest: password hashing + JWT creation/validation (unit) | ✅ |
| T2 | Pytest: register endpoint schema validation (unit) | ✅ |
| T3 | Pytest: auth flow (register → login → protected call → logout) (integration) | ✅ |
| T4 | Vitest: authStore actions (login, logout, refresh) (unit) | ✅ |
| T5 | Vitest: register + login form validation + submission (component) | ✅ |
| 10 | Manual test: register → login → protected API call → logout | ✅ |

---

## Phase 2 — CV Core ✅

| # | Task | Status |
|---|------|--------|
| 11 | Implement cvs + templates models + migrations | ✅ |
| 12 | CV CRUD endpoints (list, create, get, update, delete, copy) | ✅ |
| 13 | Seed 3 generic templates (modern, classic, minimal) | ✅ |
| 14 | CV list page with cards (title, template indicator, actions) | ✅ |
| 15 | Copy/clone CV UI (copy action on card) | ✅ |
| 16 | Build builder page layout (split pane: editor \| preview) | ✅ |
| 17 | Asset upload endpoint (filesystem) + photo UI | ✅ |
| T6 | Pytest: CV CRUD flow (create → get → update → delete) | ✅ |
| T7 | Pytest: CV copy creates independent clone | ✅ |
| T8 | Pytest: CV data isolation by user_id | ✅ |
| T9 | Pytest: photo upload (valid + invalid file, size limit) | ✅ |
| T10 | Pytest: template seed creates 3 templates | ✅ |
| T11 | Vitest: cvStore actions (create, copy, delete, save) | ✅ |
| T12 | Vitest: cvList page renders cards with actions | ✅ |
| 18 | Manual test: create CV → see in list → copy → both work | ✅ |

---

## Phase 3 — Sections + Preview ✅

| # | Task | Status |
|---|------|--------|
| 19 | ProfileSection editor + renderer | ✅ |
| 20 | ExperienceSection editor (repeatable entries) + renderer | ✅ |
| 21 | EducationSection editor + renderer | ✅ |
| 22 | SkillsSection editor + renderer | ✅ |
| 23 | ProjectsSection editor + renderer | ✅ |
| 24 | LanguagesSection editor + renderer | ✅ |
| 25 | CertificationsSection editor + renderer | ✅ |
| 26 | Section list with drag-and-drop (dnd-kit) | ✅ |
| 27 | Enable/disable section toggles | ✅ |
| 28 | Build generic-modern template renderer | ✅ |
| 29 | Build generic-classic template renderer | ✅ |
| 30 | Build generic-minimal template renderer | ✅ |
| 31 | Template switching in preview (instant) | ✅ |
| 32 | Customization panel (color, font, spacing) | ✅ |
| T13 | Pytest: section data stored correctly in JSONB | ✅ |
| T14 | Pytest: section ordering preserved through update | ✅ |
| T15 | Pytest: validation rejects invalid section data | ✅ |
| T16 | Pytest: all 3 templates render preview HTML correctly | ✅ |
| T17 | Vitest: each section editor renders + accepts input (7 tests) | ✅ |
| T18 | Vitest: section drag-and-drop reorders correctly | ✅ |
| T19 | Vitest: template switcher swaps renderer + applies config | ✅ |
| T20 | Vitest: customization panel updates CSS variables | ✅ |

---

## Phase 3.5 — Polish & UX ✅

| # | Task | Status |
|---|------|--------|
| 33 | Install lucide-react, motion, @tailwindcss/forms | ✅ |
| 34 | Create shared Modal + AccordionPanel components | ✅ |
| 35 | Replace enable/disable checkboxes with eye icons (Eye/EyeOff) | ✅ |
| 36 | Create CV modal (title + template selection) | ✅ |
| 37 | Delete CV confirmation modal | ✅ |
| 38 | Repeatable entry accordion (6 section editors) | ✅ |
| 39 | CV grid layout refinement (responsive cols, card polish) | ✅ |
| 40 | Add Section UI (dropdown to add new section types) | ✅ |
| 41 | Template Browser UI (visual template selector in builder) | ✅ |
| 42 | Motion animations across all components | ✅ |
| T35.1 | Vitest: section list eye icons, add section dropdown | ✅ |
| T35.2 | Vitest: create/delete CV modals | ✅ |
| T35.3 | Vitest: accordion expand/collapse on all 6 editors | ✅ |

---

## Phase 4 — Data Integrity & Backend Preview ✅

| # | Task | Status |
|---|------|--------|
| 43 | Section Zod validation schemas (7 sections) | ✅ |
| 44 | Backend preview endpoint (HTML renderer service + route) | ✅ |
| T44 | Pytest: preview endpoint renders correct HTML for all 3 templates | ✅ |

---

## Phase 5 — Section Instance Model (Architectural Refactor) ✅

| # | Task | Status |
|---|------|--------|
| 45 | Define `SectionInstance` type + restructure `types.ts` | ✅ |
| 46 | Update `cvStore.ts` with instance CRUD (add, remove, reorder, toggle, rename) | ✅ |
| 47 | Update `SectionList.tsx` + `SectionEditorPanel.tsx` + `SectionRegistry.tsx` for instances | ✅ |
| 48 | Update `TemplateSwitcher.tsx` + all 3 template renderers to accept instances[] | ✅ |
| 49 | Update `BuilderPage.tsx` — replace old section handlers with instance-focused ones | ✅ |
| 50 | Default: new CVs start with only 1 enabled profile instance | ✅ |
| 51 | Update backend `CVCreate` default, `renderer.py` for new format | ✅ |
| 52 | Investigate & fix sub-section CRUD controls (trace EducationEditor → PATCH → reload) | ✅ |
| T45 | Update existing test data shapes for new SectionInstance format | ✅ |
| T46 | Vitest: section instance CRUD (add, remove, reorder, toggle, rename) | ✅ |

---

## Phase 6 — Add Section Modal & Customization UX ✅

| # | Task | Status |
|---|------|--------|
| 53 | Grid modal for adding sections (replaces dropdown, 3-column card grid) | ✅ |
| 54 | Collapsible customization panel (toggle icon in builder header) | ✅ |
| 55 | Inline section title editing (click title → text input) | ✅ |
| T47 | Vitest: add section grid modal renders all types, click adds instance | ✅ |
| T48 | Vitest: customization panel hidden by default, icon toggles visibility | ✅ |

---

## Phase 7 — PDF Export & Auto-Save ✅

| # | Task | Status |
|---|------|--------|
| 56 | In-process PDF export (Playwright) | ✅ |
| 57 | Preview = PDF exact match (print styles) | ✅ |
| 58 | Auto-save with debounce (3s) | ✅ |
| 59 | Validation errors display (Zod + components) | ✅ |
| 60 | Toast notifications, loading states, empty states | ✅ |
| 61 | Error handling UI (ErrorBoundary, axios toasts) | ✅ |
| 56.5 | Routing paths overhaul (AppLayout, Settings, 404) | ✅ |
| T49 | Pytest: PDF export returns valid PDF for all templates | ✅ |
| T50 | Pytest: PDF content matches CV data | ✅ |
| T51 | Pytest/TS: auto-save debounces correctly (unit) | ☐ |
| T52 | Pytest: PDF export fails gracefully for non-existent CV | ✅ |
| T53 | Vitest: PDF export trigger + success/fail handling | ☐ |
| T54 | Vitest: auto-save debounced save fires at correct interval | ☐ |
| T55 | Vitest: toast system renders success/error (component) | ☐ |
| T56 | E2E: full user journey (login → create → edit → switch template → export → logout) | ☐ |
| 62 | Final integration testing | ☐ |

---

## Phase 8 — Production Deployment ✅

| # | Task | Status |
|---|------|--------|
| 8.1 | Docker Compose: add api service with uploads volume | ✅ |
| 8.2 | Multi-stage Dockerfile (frontend builds inside API image) | ✅ |
| 8.3 | dev.sh: playwright install, .env loading, --prod/--build flags | ✅ |
| 8.4 | Rate limiting with slowapi (auth 10/min, global 100/min) | ✅ |
| 8.5 | Enhanced health check + security middleware | ✅ |
| 8.6 | DEPLOY.md documentation | ✅ |

---

## Phase 9 — Builder UX & Polish ✅

| # | Task | Status |
|---|------|--------|
| 63 | Delete confirmation modal on section remove | ✅ |
| 64 | Sub-section accordions closed by default | ✅ |
| 65 | Sub-section drag-to-reorder via dnd-kit (6 editors) | ✅ |
| 66 | Builder tabs: replace side-by-side panel with "Content" / "Customize" tabs | ✅ |
| T9.1 | Vitest: section delete modal renders and confirms/aborts | ✅ |
| T9.2 | Vitest: accordion starts closed by default | ✅ |
| T9.3 | Vitest: sub-section drag reorders entries array correctly | ✅ |
| T9.4 | Vitest: builder tab switching renders correct panel | ✅ |
| 67 | Manual test: full flow — reorder sub-sections in experience, confirm order persists after reload | ✅ |

---

## Phase 9.5 — Bug Fixes for Phase 9 ✅

| # | Task | Status |
|---|------|--------|
| 9.5.1 | Install @testing-library/user-event (missing dep) | ✅ |
| 9.5.2 | Fix localStorage not available in jsdom (authStore tests) | ✅ |
| 9.5.3 | Delete stale sectionInstanceStore.test.ts (methods removed from cvStore) | ✅ |
| 9.5.4 | Fix SectionEditors.test.tsx: click accordion to expand before asserting fields | ✅ |
| 9.5.5 | Fix CustomizePanel.test.tsx: add missing store mocks, rewrite T48 for tab layout | ✅ |
| 9.5.6 | Single DndContext refactor: unify nested DndContexts to fix sub-section drag auto-save | ✅ |
| T9.5 | All frontend tests pass (0 failures) | ✅ |

---

## Phase 10 — Customize Tab Enhancement & UI Cleanup ✅

| # | Task | Status |
|---|------|--------|
| 70 | Remove Palette button from BuilderPage header | ✅ |
| 71 | Remove template "Change" badge from BuilderPage header | ✅ |
| 72 | Add `templateId` and `onTemplateChange` props to `CustomizePanel` + inline template selector (3 cards: Modern, Classic, Minimal) | ✅ |
| 73 | Remove `TemplateBrowser` modal component entirely | ✅ |
| 74 | Remove `showTemplateBrowser` state and related logic from `BuilderPage` | ✅ |
| 75 | Clean up unused imports in `BuilderPage` | ✅ |
| T10.1 | Vitest: CustomizePanel renders inline template selector with correct active state | ✅ |
| T10.2 | Vitest: clicking a template card triggers `onTemplateChange` | ✅ |
| T10.3 | Vitest: template selector only visible in Customize tab (not Content) | ✅ |
| 76 | Manual test: switch template from Customize → preview updates → persists after reload | ✅ |

---

## Phase 10.5 — Per-Instance Style Overrides ✅

| # | Task | Status |
|---|------|--------|
| 78 | Add `SectionStyle` type (`font`, `color`, `weight`) + `style?: SectionStyle` to `SectionInstance` in `types.ts` | ✅ |
| 79 | Add `section-{type}` CSS class to preview wrapper in `SectionPreviewPanel.tsx` | ✅ |
| 80 | Apply `instance.style` inline overrides (font, color, weight) in `SectionPreviewPanel` — on wrapper div + heading | ✅ |
| 83 | Wire `handleUpdateStyle` in `BuilderPage.tsx` → `setLocalInstances` | ✅ |
| 84 | In `handleTemplateChange`, strip `style` from all instances before saving | ✅ |
| 86 | Update backend `renderer.py` to apply per-instance styles in `render_instance_panel` | ✅ |
| 87 | **Revert SectionEditorPanel** — remove style imports, `onUpdateStyle` prop, style state/UI. Restore to original simple component. | ✅ |
| 88 | **Revert SectionList** — remove `onUpdateStyle` from Props and threading. | ✅ |
| 89 | **Rewrite CustomizePanel** — remove Colors/Fonts/Spacing sub-tab bar. Add `instances` + `onUpdateStyle` props. Structure: Template selector → collapsible "Global" section (all colors, fonts, spacing) → per-instance style cards (font/color/weight each). | ✅ |
| 90 | **Update BuilderPage** — remove `onUpdateStyle` from `<SectionList>`, pass `instances` + `onUpdateStyle` to `<CustomizePanel>`. | ✅ |
| T10.4 | Vitest: update CustomizePanel tests for combined Global + section overrides | ✅ |
| T11.2 | Vitest: `SectionPreviewPanel` renders with per-instance styles applied | ☐ |
| T11.3 | Vitest: `section-{type}` class present on preview wrapper | ☐ |
| T11.4 | Vitest: template change strips per-instance styles | ☐ |
| T11.5 | Pytest: backend renders per-instance styles | ☐ |
| 85 | Manual test: set per-instance style → preview updates → switch template → styles reset | ☐ |

---

## Phase 11 — UX Polish: Style Accordions, Login Persistence, Home Page ✅

| # | Task | Status |
|---|------|--------|
| 91 | Make per-section style cards accordions (expand/collapse with chevron) in CustomizePanel | ✅ |
| 92 | Fix auth store — initialize tokens from `localStorage` synchronously to prevent login flash on refresh | ✅ |
| 93 | Create public `HomePage` at `/` with app name + login/register buttons | ✅ |
| 94 | Restructure routes: `/` → HomePage, `/dashboard` → CvListPage (protected) | ✅ |
| 95 | Update LoginForm fallback redirect from `"/"` to `"/dashboard"` | ✅ |
| 96 | Add hydrated guard to ProtectedRoute to prevent redirect flash | ✅ |
| T11.1 | Vitest: section style accordion expands/collapses on click | ☐ |
| T11.2 | Vitest: auth store initializes from localStorage correctly | ☐ |

---

## Phase 11 Bugfix — Route Cleanup ✅

| # | Task | Status |
|---|------|--------|
| R1 | Fix CvListPage: navigate to `/dashboard/builder/:id` (was 404) | ✅ |
| R2 | Fix CreateCvModal: navigate to `/dashboard/builder/:id` (was 404) | ✅ |
| R3 | Fix LoginForm: hardcode redirect to `/dashboard` (ignore `location.state.from`) | ✅ |
| R4 | Fix BuilderPage back button: `/` → `/dashboard` | ✅ |
| R5 | Fix AppLayout brand link: `"/dashboard"` → `"/"` (public home), dynamic "My CVs" in builder | ✅ |
| R6 | Fix AppLayout "My CVs" link: `/` → `/dashboard` | ✅ |
| R7 | Fix AppLayout Settings link: `/settings` → `/dashboard/settings` | ✅ |
| R8 | Fix NotFoundPage "Go to Dashboard": `/` → `/dashboard` | ✅ |
| R9 | Fix ErrorBoundary "Go to Dashboard": `/` → `/dashboard` | ✅ |
| R10 | Fix CvList test: route path `/` → `/dashboard` | ✅ |

---

## Phase 11.5 — Home Page Polish & Navbar Refinements ✅

| # | Task | Status |
|---|------|--------|
| H1 | Redesign HomePage with full marketing layout (emerald theme, features grid, conditional CTAs) | ✅ |
| H2 | AppLayout: show "My CVs" link instead of "Aergia" logo when inside builder page | ✅ |
| H3 | AppLayout brand logo always links to `/` (public home) | ✅ |

---

## Phase 12 — User-Defined Templates ✅

### Backend

| # | Task | Status |
|---|------|--------|
| U1 | Alembic migration: add `content` (TEXT) and `user_id` (UUID FK) columns to `templates` table | ✅ |
| U2 | Update Template model with new columns | ✅ |
| U3 | Update Pydantic schemas (`TemplateDetail` includes `content`, list includes `is_user_template` flag) | ✅ |
| U4 | Add `POST /api/v1/templates/user` — upload user template (multipart: name + HTML file) | ✅ |
| U5 | Add `DELETE /api/v1/templates/user/{id}` — delete own user template | ✅ |
| U6 | Update `GET /api/v1/templates` to include current user's templates | ✅ |
| U7 | Add `render_user_template` to `renderer.py` — injects `window.__CV_DATA__` into user HTML | ✅ |
| U8 | Update `render_preview` to accept optional `template_content` param | ✅ |
| U9 | Update PDF service to fetch template content for user templates | ✅ |
| U10 | Update preview endpoint to pass template content | ✅ |

### Frontend

| # | Task | Status |
|---|------|--------|
| U11 | Create `web/src/lib/api/templates.ts` — API client for user template CRUD | ✅ |
| U12 | Create `web/src/lib/store/userTemplateStore.ts` — Zustand store (list cache) | ✅ |
| U13 | Create `UserTemplateRenderer.tsx` — iframe with `srcdoc` + injected data | ✅ |
| U14 | Create `TemplateSelectorModal.tsx` — modal showing system + user templates, upload button | ✅ |
| U15 | Update `CustomizePanel.tsx` — replace inline template list with "Change Template" → modal; hide Global for user templates | ✅ |
| U16 | Update `TemplateSwitcher.tsx` — route `user_*` templates to iframe renderer | ✅ |
| U17 | Update `BuilderPage.tsx` — fetch template content, reset customizations on switch | ✅ |
| U18 | Update `CreateCvModal.tsx` — list user templates alongside system ones | ✅ |

### Docs & Tests

| # | Task | Status |
|---|------|--------|
| U19 | Write `TEMPLATE_GUIDE.md` — user template format, data shape, examples | ✅ |
| U20 | Backend tests: user template upload, delete, render | ❌ (cancelled due to test infrastructure issues) |
| U21 | Frontend tests: CustomizePanel, TemplateSwitcher, TemplateSelectorModal | ❌ (cancelled due to test infrastructure issues) |

---

## Architecture & Configuration Docs (Completed)

- Single-Origin Design (FastAPI serves SPA + API)
- Tech Stack finalized
- VPS specs documented
- Database schema (users, cvs, templates)
- CV Section data model (7 section types)
- Seed templates (Modern, Classic, Minimal)
- API endpoints (Auth, CVs, Assets, Templates)
- Auth flow (bcrypt, JWT, Zustand)
- PDF flow (Playwright in-process)
- File storage (local filesystem)
- Template system architecture
- State management (Zustand stores)
- Docker Compose configuration
- Deployment checklist
- Security summary
- Testing summary (37 tests)
- Folder structure

---

*End of completed plans archive. New roadmap begins in PLAN.md.*