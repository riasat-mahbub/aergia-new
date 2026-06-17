---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KZJ0PHASE2QA
TYPE: bug
STATUS: PROPOSED
PRIORITY: High
SEVERITY: High
EFFORT: M
OWNER: riasat
CONFIDENCE: High
TAGS:
- phase-2
- customization
- wire-mismatch
RELATIONS:
  part_of:
    - FEAT-01KZJ0PHASE2QA-phase-2-three-axis-customize-panel
AFFECTS:
  files:
    - api/app/schema/models.py
    - api/app/services/renderer/resolve.py
    - web/src/components/customization/CustomizePanel.tsx
    - web/src/components/customization/StyleEditor.tsx
    - web/src/components/template-creator/TemplateWizard.tsx
LINKS:
  plan: local://ast-pipeline-phase-2-plan-v5.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: 2026-08-06
UPDATED_AT: 2026-08-06
---

# Customizations silently drops panel writes to legacy {colors, fonts, spacing, flags}

## Background

The customize panel and the template wizard write a v1 customizations
shape:

```json
{ "colors": { "accent": "#..." }, "fonts": { "body": "..." } }
```

The `Customizations` Pydantic model only declares canonical v2 fields
(`accent_color, body_font, heading_font, default_text_align, spacing,
flags, per_section`) with `extra="ignore"`. The result: panel writes to
`colors.accent` / `fonts.body` are silently dropped before reaching the
resolver. The renderer applies the template default instead. User edits
to accent color / body font / heading font are lost on every save.

## Investigation

Symptom: opening a CV built on `generic-modern`, editing accent color in
the customize panel's Global block, saving, then re-loading — accent
reverts to `manifest.global_styles["accent_color"]`. Reproducible across
both the customize panel and the template wizard.

Root cause located in two places:
1. `api/app/schema/models.py:Customizations` — no `colors`, `fonts`,
   `spacing` (dict), or `flags` (dict) fields.
2. `api/app/db/seed.py:build_manifest` — bridges between the legacy
   `default_customizations` shape and the v2 manifest at seed time, which
   is what makes the v3 templates render correctly today.

The resolver never sees the panel's writes — they vanish at the model
boundary.

## Decision

Phase 2 fixes this as Step 1:

1. Add `model_validator(mode="before")` to `Customizations` that rejects
   `colors` and `fonts` top-level keys with a `ValidationError`.
2. Add `app/services/legacy_customizations.py:migrate_legacy_customizations`
   to map the legacy shape to canonical fields.
3. Add `coerce_customizations(raw)` in `app/services/cv.py` that runs the
   migrator then validates. Three call-sites updated:
   `api/app/routes/render.py`, `api/app/routes/cvs.py`,
   `api/app/services/pdf.py`.

Phase 3 will add a `Customizations` UI to the customize panel that writes
the canonical shape, closing the loop. In Phase 2 the panel stops writing
`colors`/`fonts`/`spacing`/`flags` because `StyleEditor.tsx` is stubbed.

## Implementation

See the v5 plan Step 1 in `local://ast-pipeline-phase-2-plan-v5.md`.
Also:

- 7 migrator tests in new `tests/test_legacy_customizations.py`.
- 3 schema-validation tests in `tests/test_schema.py` (legacy rejected,
  canonical passes, both axes).
- The validator `model_validator` runs on every `Customizations.model_validate`
  call; legacy payloads blow up loud instead of silently dropping.

## Verification

```bash
cd api && rm -f data/aergia.test.db && .venv/bin/pytest -q
```

Plus the smoke command at v5 plan Step 7 / Smoke A:

```
A: #abc Inter
B: OK legacy rejected
```

## Follow-up

- Phase 3: replace the panel's `<StyleEditor>` with a new component that
  writes canonical `Customizations`.
- The legacy migrator stays; tracked rows in the DB continue to migrate
  on read until each user re-saves.
