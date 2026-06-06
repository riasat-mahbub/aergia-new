---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KZ4CPQ28S0WP6HJZF16D80CC
TYPE: feature
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS:
  - api/app/schemas/manifest.py
  - web/src/components/customization/StyleEditor.tsx
  - api/app/db/seed.py
  - api/app/routes/templates.py
  - api/app/services/renderer/ir.py
  - api/app/db/seed.py
  - api/app/app.py
  - api/tests/test_cascading_styles.py
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-03T18:03:18.472535+00:00'
UPDATED_AT: '2026-08-03T18:03:18.472535+00:00'
---

# Toggleable underline under section titles

## Background
## Investigation

Plan loaded from `local://section-title-underline-toggle-plan.md` (6 steps). IR is the shared render path for live preview and PDF, so the change lives in one place: `_build_section_panel` in `api/app/services/renderer/ir.py`. The `flags` customizations bucket mirrors the existing `colors`/`fonts`/`spacing` pattern; `boolean` schema entries route to it in both `build_manifest` and `_build_default_customizations`.

## Decision

Default off; per CV. Underline uses `border-bottom:1px solid var(--heading, #1f2937)` + `padding-bottom:4px`. The CSS var keeps the underline in sync with the heading color for free. No new state in Zustand; the existing `BuilderPage.handleCustomizationsChange` already persists the whole `customizations` object.

## Implementation

Schema: widened `StyleVarSchema.type` to include `"boolean"` in both `api/app/schemas/manifest.py` and `web/src/components/customization/StyleEditor.tsx`.
Seed: each of the three templates gained a `flags` bucket (`{"underline_section_titles": False}`); `build_manifest` emits a `boolean` schema entry. `_build_default_customizations` routes `boolean` to `flags` so user-created templates match.
Renderer: `_resolve_flags` merges manifest defaults with user overrides; `build_ir` puts the result on `context["flags"]`; `_build_section_panel` appends the border-bottom + padding to the heading style when the flag is on.
UI: `StyleEditor.DEFAULT_SCHEMA` adds the toggle; `updateVar`/`getVarValue` consult a new `flags` bucket; the new `case "boolean"` renders a role="switch" toggle identical in shape to the per-section "Show Title" pill.
Seed refresh: existing seed rows now receive an updated `default_customizations` on every boot, so a pre-existing DB picks up the new `flags` bucket without a manual migration. User-created templates are untouched. Lifespan also calls `session.commit()` so a fresh DB seeds correctly (pre-existing missing commit fixed).

## Verification

- Backend: `pytest tests/test_cascading_styles.py tests/test_preview.py tests/test_section_renderers.py` → 28 passed.
- New tests in `test_cascading_styles.py` cover: flag true emits `border-bottom:1px solid var(--heading` inside the heading `<h2>`, flag false/missing produces no border, and the cascade references `var(--heading)`.
- Frontend: `tsc -b && vite build` clean; `vitest run SectionEditors.test.tsx` 6/6.
- Browser smoke (dev stack): created CV, added Experience, toggled Underline Section Titles on → preview h2 carries `border-bottom:1px solid var(--heading, #1f2937);padding-bottom:4px`. Recolored Heading to `#ff0000` → `--heading` updated, h2 cascade picks it up. Toggled off → border disappears. Saved, reloaded → state persisted.
- PDF export via Playwright (smoke): `PDF exported successfully` toast confirmed. Live preview and PDF share `HTMLBackend._format`, so no separate PDF test is needed.

## Follow-up

None.
