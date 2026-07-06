---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KZJ0PHASE2QA
TYPE: bug
STATUS: DONE
SEVERITY: Medium
EFFORT: M
OWNER: riasat
CONFIDENCE: High
TAGS:
- phase-2
- template-authoring
- deprecation
RELATIONS:
  part_of:
    - FEAT-01KZJ0PHASE2QA-phase-2-three-axis-customize-panel
  superseded_by:
    - TASK-01KZJ0PHASE2QA-phase-3-template-creator-and-global-customizations
AFFECTS:
  files:
    - web/src/components/template-creator/TemplateWizard.tsx
    - web/src/components/customization/StyleEditor.tsx
    - api/app/db/seed.py
    - api/app/routes/templates.py
LINKS:
  plan: local://ast-pipeline-phase-2-plan-v5.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: 2026-08-06
UPDATED_AT: 2026-08-06
---

# TemplateWizard writes legacy customizations shape incompatible with v2

## Background

`web/src/components/template-creator/TemplateWizard.tsx` runs the
"Styles" step on top of `<StyleEditor>`. It reads `customizations.colors`
and `customizations.fonts` and emits a `globalStyleSchema` derived from
those keys, then persists the result as `default_customizations`. None of
this matches the v2 `TemplateManifest.global_styles` /
`Customizations.{accent_color,body_font,heading_font}` shape.

Phase 1 made the renderer pipeline v2-only, but left both authoring
surfaces (`TemplateWizard`, the customize panel's `<StyleEditor>`) on
the v1 representation. After Phase 2:
- The wizard produces manifests with a `default_customizations` shape
  that Pydantic's `Customizations` rejects.
- `api/app/routes/templates.py:_default_customizations_from_manifest`
  re-derives the legacy shape from `manifest.global_styles` at write
  time, which masks the bug from system templates but not user
  templates.

## Investigation

Three legacy surfaces in flight:
1. `TemplateWizard.tsx`'s `handleStyleChange` builds a `globalStyleSchema`
   from `customizations.{colors,fonts,spacing}`. Result saved to
   `manifest.default_customizations` and as `manifest.globalStyleSchema`
   field that the v2 schema doesn't carry.
2. `api/app/db/seed.py:build_manifest` reads the legacy shape from
   `SEED_TEMPLATES` and writes a v2 manifest. This is fine for seeding
   but not for runtime authored templates.
3. `api/app/routes/templates.py:171` derives a legacy-shape
   `default_customizations` from a v2 manifest at upload time. Round-trip
   is symmetric and inert.

The wizard is the only consumer of `<StyleEditor>` after this phase.
Removing the editor and stubbing the wizard stops the broken writes.

## Decision

Phase 2 stub:
- `StyleEditor.tsx` is deleted. No other file imports it.
- `TemplateWizard.tsx` is replaced with a deprecated banner that points to
  the Phase 3 tracker entry. v2 template authoring already lives in
  `POST /templates/user` (manifest.json upload).

Phase 3 rebuild:
- New wizard writes against `TemplateManifest.global_styles` and
  `Customizations.{accent_color, body_font, heading_font}`.
- The new wizard's UI surface replaces `<StyleEditor>` rather than
  reusing it.

## Implementation

v5 plan Steps 5a and 5b. The stub renders a warning to template authors
with a one-paragraph explanation, no functional behaviour. Existing tests
that hit `<TemplateWizard>` continue to pass (it still exports `default`).

## Verification

```bash
cd web && grep -rn 'StyleEditor' web/src --include='*.tsx' --include='*.ts'    # zero
cd web && grep -rn 'TemplateWizard' web/src --include='*.tsx' --include='*.ts'   # only the stub file
cd web && npm run build                                                          # 0
```
Closed 2026-08-08 by `FEAT-01KZPHASE6STEP1-phase-6-content-only-authoring`. The template-authoring surface is deleted entirely; the customize panel is the sole styling surface. The wizard, the multipart upload, the user-templates routes, and the user-templates section of `TemplateSelectorModal` are all gone. The closed-vocabulary manifests (modern, classic, minimal) remain as the only templates available to users.

See `local://phase-6-content-only-authoring-plan.md` for the cutover plan.
