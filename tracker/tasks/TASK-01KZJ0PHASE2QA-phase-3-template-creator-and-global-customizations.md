---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KZJ0PHASE2QA
TYPE: task
STATUS: PROPOSED
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
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: 2026-08-06
UPDATED_AT: 2026-08-06
---

# Phase 3 — v2 template creator + global customizations UI

## Background

Phase 2 stubbed `TemplateWizard.tsx` (deprecated banner) and deleted
`StyleEditor.tsx` because both wrote the legacy v1 customizations shape.
The Phase 2 panel deliberately exposes no global `Customizations` UI —
per-CV body font / accent color / heading font / spacing continue to
flow from `manifest.global_styles` only. Phase 3 rebuilds both, against
the v2 `TemplateManifest` and the canonical `Customizations` shape.

## Plan

### 1. v2-aware template creator

Rewrite `TemplateWizard.tsx` against the v2 `TemplateManifest` schema:

- "Styles" step writes `manifest.global_styles` directly (no
  `default_customizations` intermediary). Keys: `accent_color`, `body_font`,
  `heading_font`, `bg_sidebar`, `divider`, plus any color the manifest
  declares as a `ZoneStyle.styles` field.
- "Layout" step persists `manifest.layout_defaults.spacing`
  (`compact|comfortable|minimal`) plus per-zone CSS overrides.
- Replace `<StyleEditor>` with a v2-aware component (or fork it with a
  new name; deletion + restoration is also acceptable). Schema source:
  `manifest.global_styles` + `manifest.zones[*].styles`.
- Save flow stays on `POST /templates/user`, but the manifest payload
  is the v2 schema, not the wrapped v1 shape.
- Remove the deprecated banner stub.

### 2. Global Customizations group in the panel

Add a fourth `<details>` group to `CustomizePanel.tsx`: "Document".

Controls:
- Accent color (`Customizations.accent_color`) — color picker + hex.
- Body font (`Customizations.body_font`) — `<select>` with the same font
  options as `<StyleEditor>`'s `DEFAULT_SCHEMA`.
- Heading font (`Customizations.heading_font`) — `<select>`.
- Template spacing (`Customizations.spacing`) — three-way radio
  (`compact|comfortable|minimal`).
- Maybe: `default_link_style` flag from the canonical `flags` map.

Writes flow through a new prop `onCustomizationsChange(customizations)`
on `CustomizePanel`. `BuilderPage` already owns `localCustomizations`;
add `handleUpdateCustomizations` that mirrors `handleUpdateStyle`:
validate with `customizationsSchema`, persist only if any canonical field
is non-empty.

This closes the loop opened in Phase 2 Step 1's "BUG:
Customizations silently drops panel writes".

### 3. Document v2 template authoring

- Update `AGENTS.md` and `PLAN.md` to remove the "Phase 3 placeholder"
  note.
- Update `tracker/README.md` to reflect the resolved state.
- Consider deleting the v5 plan from `local://` once this lands.

## Out of scope (Phase 4+)

- Per-field font wire-key (`text[key].font`) re-introduction if the section
  needs to override the cascade.
- DOCX export renderer (separate task).
- Multi-template preview side-by-side.

## Verification (proposed)

- `pytest -q` — same count as end of Phase 2 (no backend changes).
- `cd web && npm run build` — 0.
- Template wizard smoke: open `/templates/new`, fill basics, layout,
  styles (accent / fonts / spacing), save; verify the resulting row's
  `manifest` is v2-shaped and renders correctly.
- Customize panel smoke: open a CV, change accent color from the panel,
  verify the resolved CSS vars pick it up via the new direct write path.
