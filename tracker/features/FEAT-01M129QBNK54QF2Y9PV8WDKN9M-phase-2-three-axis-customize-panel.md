---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN9M
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
EFFORT: L
OWNER: riasat
CONFIDENCE: High
TAGS:
- phase-2
- ast-pipeline
- customize-panel
- three-axis
RELATIONS:
  depends_on:
  - ADR-01M129QBNK54QF2Y9PV8WDKN6R
  related:
  - BUG-01M129QBNK54QF2Y9PV8WDKN7C
  - BUG-01M129QBNK54QF2Y9PV8WDKN7D
AFFECTS:
  files:
  - api/app/schema/models.py
  - api/app/services/legacy_customizations.py
  - api/app/services/cv.py
  - api/app/services/renderer/resolve.py
  - api/app/routes/render.py
  - api/app/routes/cvs.py
  - api/app/services/pdf.py
  - api/app/services/renderer/builders/__init__.py
  - web/src/lib/api/render.ts
  - web/src/lib/store/supportStore.ts
  - web/src/pages/BuilderPage.tsx
  - web/src/components/customization/CustomizePanel.tsx
  - web/src/components/customization/StyleEditor.tsx
  - web/src/components/template-creator/TemplateWizard.tsx
  - web/src/lib/validators/sections.ts
  - web/src/lib/sections/types.ts
LINKS:
  plan: local://ast-pipeline-phase-2-plan-v5.md
  closeout: local://phase-7-ast-pipeline-closeout.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-06T00:00:00+00:00'
UPDATED_AT: '2026-08-08T22:36:00+00:00'
---

# Phase 2 — Customize panel on the three-axis wire (Customizations cut to canonical)

## Background

Phase 1 cut the renderer over from a string-concat IR to a typed three-axis AST. The wire shape, resolver, HTML renderer, PDF plumbing, seed v2 manifests, and codegen are in place. What remains is the user surface — the customize panel and persistence — plus a wire-shape bug in `Customizations` that silently drops legacy keys.

## Decision

Phase 2 delivered a single cutover to canonical shapes:

1. The customize panel writes only `style.layout / .subsection / .policy / .text[key]` keys on `SectionInstanceStyle`. Legacy `SectionStyle` keys are NEVER written.
2. Per-CV `Customizations` accepts only the canonical v2 fields (`accent_color / body_font / heading_font / default_text_align / spacing (preset enum) / flags / per_section`). Legacy `{colors, fonts, spacing, flags}` top-level keys are rejected at the boundary.
3. `legacy_style` on `SectionInstance` is deleted from the Python model and from codegen.
4. The `StyleEditor.tsx` and `TemplateWizard.tsx` files were stubbed in Phase 2; Phase 3 rebuilt the global customizations editor against the v2 manifest; Phase 6 deleted the user-template authoring surface entirely.
5. The customize panel exposes the "Document" disclosure (accent / body-font / heading-font / spacing) which writes canonical top-level `Customizations`.

The full Phase 2 plan is at `local://ast-pipeline-phase-2-plan-v5.md`. The shipped closeout lives at `local://phase-7-ast-pipeline-closeout.md`.

## Implementation

Phases are ordered so the tree builds after each step:

- **Step 1:** Backend `Customizations` rejects legacy top-level keys via `model_validator(mode="before")`. New `app/services/legacy_customizations.py` migrates stored legacy rows on read. `coerce_customizations` helper centralises the migrator + validate. Three call-sites updated.
- **Step 2:** Backend `_drop_none_features` becomes real — zero `break_before`, `keep_together`, `heading_keeps_with_first` flags when their `RendererSupport` is `NONE`.
- **Step 3:** `legacy_style` removed from `SectionInstance`. Builder updated. Codegen rerun.
- **Step 4:** Frontend render client + Zustand store with `retry` action. `BuilderPage` mounts `ensureLoaded()`. 4 tests.
- **Step 5:** `StyleEditor.tsx` deleted. `TemplateWizard.tsx` stubbed. `CustomizePanel.tsx` rewritten — three `<details>` disclosure groups, four write helpers, per-axis gates from `useSupportStore`.
- **Step 6:** `sectionStyleHasValues` rewritten for three axes. `handleUpdateStyle` narrowed. Three Zod validators added (`.strict()`). Test rewrites on `CustomizePanel.test.tsx` and `BuilderPage.handleUpdateStyle.test.ts`.
- **Step 7:** Final verification — backend full suite, codegen check, frontend build, targeted suites, two smoke commands.
- **Phase 3:** New global "Document" disclosure on `CustomizePanel` writes `accent_color / body_font / heading_font / spacing` to canonical `Customizations`.
- **Phase 6 step 1:** User-template authoring surface deleted. Wizard, multipart upload, user-templates routes, and the user-templates section of `TemplateSelectorModal` are all gone. The closed-vocabulary manifests (modern, classic, minimal) are the only templates.

## Verification

See plan DoD: `pytest -q`, `codegen_schema.py --check`, `npm run build`, all targeted tests, two smoke commands. Defined in `local://ast-pipeline-phase-2-plan-v5.md`. Re-verified end-to-end in the Phase 7 closeout (`local://phase-7-ast-pipeline-closeout.md`) via `./dev.sh --smoke` (Phase 8 hardening gate).

## Follow-up

Phase 3 (TASK `TASK-01KZJ0PHASE2QA`) shipped the global customizations editor and was itself closed in Phase 6 when user-template authoring was removed. Codegen output is unchanged except for the `legacy_style` removal.

<!-- Migrated from FEAT-01KZJ0PHASE2QA during the schema-4 cutover. -->
