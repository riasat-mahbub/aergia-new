---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KZJ0PHASE2QA
TYPE: task
STATUS: IN_PROGRESS
PRIORITY: Medium
EFFORT: L
OWNER: riasat
CONFIDENCE: High
TAGS:
- phase-3
- template-authoring
- customization
RELATIONS:
  supersedes:
  - BUG-01KZJ0PHASE2QA-template-wizard-on-legacy-paths
  depends_on:
  - FEAT-01KZJ0PHASE2QA-phase-2-three-axis-customize-panel
AFFECTS:
  files:
  - web/src/components/template-creator/TemplateWizard.tsx
  - web/src/components/customization/StyleEditor.tsx
  - web/src/components/customization/CustomizePanel.tsx
  - web/src/lib/api/templates.ts
LINKS:
  plan: local://ast-pipeline-phase-2-plan-v5.md
  closeout: local://phase-7-ast-pipeline-closeout.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-06T00:00:00+00:00'
UPDATED_AT: '2026-08-08T22:36:00+00:00'
---

# Phase 3 — v2 template creator + global customizations UI

## Background

Phase 2 stubbed `TemplateWizard.tsx` (deprecated banner) and deleted `StyleEditor.tsx` because both wrote the legacy v1 customizations shape. The Phase 2 panel deliberately exposes no global `Customizations` UI — per-CV body font / accent color / heading font / spacing continued to flow from `manifest.global_styles` only. Phase 3 rebuilt the global customizations UI; Phase 6 deleted user-template authoring entirely.

## Shipped

- **Global Customizations group on the customize panel** (`CustomizePanel.tsx`): accent color picker + hex (`Customizations.accent_color`), body font select (`Customizations.body_font`), heading font select (`Customizations.heading_font`), spacing radio (`compact | comfortable | minimal`). Writes flow through `onCustomizationsChange`.
- `BuilderPage.handleUpdateCustomizations` mirrors `handleUpdateStyle` and persists canonical fields.
- The deprecated `TemplateWizard` banner was in place during Phase 3 / 4 / 5. Phase 6 step 1 removed the user-template authoring surface entirely.

## Out of scope (deferred)

- Per-field font wire-key (`text[key].font`) re-introduction if a section needs to override the cascade.
- DOCX export renderer (separate task).
- Multi-template preview side-by-side.

## Disposition

Done in Phase 3 (CustomizePanel "Document" group) and subsequently closed by Phase 6 step 1 (template authoring removed). The wizard is intentionally not being revived; templates are now a closed, typed vocabulary owned by Aergia (modern, classic, minimal) and not user-authored. See `local://phase-7-ast-pipeline-closeout.md`.

## Verification

`pytest -q`, `npm run build`, and the `./dev.sh --smoke` Phase 8 gate all pass with the closed customizations wire.
