---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KZHR8P3K22BFSPZTY8TM8TNE
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: High
EFFORT: M
OWNER: riasat
CONFIDENCE: Medium
TAGS:
- phase-2
- customization
- wire-mismatch
- migrated
RELATIONS:
  part_of:
  - FEAT-01KZJ0PHASE2QA-phase-2-three-axis-customize-panel
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
  - web/src/components/customization/CustomizePanel.tsx
  - web/src/components/customization/StyleEditor.tsx
  - web/src/components/template-creator/TemplateWizard.tsx
LINKS:
  plan: local://phase-7-closeout-phase-8-hardening-plan.md
  source: tracker/bugs/BUG-01KZJ0PHASE2QA-customizations-wire-mismatch.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-08T22:35:29.268005+00:00'
UPDATED_AT: '2026-08-08T22:35:29.268005+00:00'
---

# Customizations silently drops panel writes to legacy {colors, fonts, spacing, flags}

## Background

Migrated from `tracker/bugs/BUG-01KZJ0PHASE2QA-customizations-wire-mismatch.md` (legacy duplicate ID; original moved to `tracker-legacy/phase-7/`). The customize panel and template wizard wrote a v1 `{ "colors": { "accent": "..." }, "fonts": { "body": "..." } }` shape that Pydantic's `Customizations` rejected after Phase 1.

The `Customizations` Pydantic model only declared canonical v2 fields (`accent_color, body_font, heading_font, default_text_align, spacing, flags, per_section`) with `extra="ignore"`. The result: panel writes to `colors.accent` / `fonts.body` were silently dropped before reaching the resolver. The renderer applied the template default instead. User edits to accent color / body font / heading font were lost on every save.

## Investigation

Symptom: opening a CV built on `generic-modern`, editing accent color in the customize panel's Global block, saving, then re-loading — accent reverts to `manifest.global_styles["accent_color"]`. Reproducible across both the customize panel and the template wizard.

Root cause located in two places:

1. `api/app/schema/models.py:Customizations` — no `colors`, `fonts`, `spacing` (dict), or `flags` (dict) fields.
2. `api/app/db/seed.py:build_manifest` — bridges between the legacy `default_customizations` shape and the v2 manifest at seed time, which is what made the v3 templates render correctly today.

## Decision

Phase 2 fixed this as Step 1:

1. Add `model_validator(mode="before")` to `Customizations` that rejects `colors` and `fonts` top-level keys with a `ValidationError`.
2. Add `app/services/legacy_customizations.py:migrate_legacy_customizations` to map the legacy shape to canonical fields.
3. Add `coerce_customizations(raw)` in `app/services/cv.py` that runs the migrator then validates. Three call-sites updated: `api/app/routes/render.py`, `api/app/routes/cvs.py`, `api/app/services/pdf.py`.

Phase 3 added a `Customizations` UI to the customize panel that writes the canonical shape, closing the loop. In Phase 2 the panel stopped writing `colors`/`fonts`/`spacing`/`flags` because `StyleEditor.tsx` was stubbed.

## Implementation

- 7 migrator tests in `api/tests/test_legacy_customizations.py`.
- 3 schema-validation tests in `api/tests/test_schema.py` (legacy rejected, canonical passes, both axes).
- The validator `model_validator` runs on every `Customizations.model_validate` call; legacy payloads blow up loud instead of silently dropping.
- Phase 3 added the CustomizePanel "Document" disclosure writing canonical top-level fields.
- Phase 6 deleted the user-template authoring surface entirely; the wizard, the multipart upload, the user-templates routes, and the user-templates section of `TemplateSelectorModal` are gone.

## Verification

- `cd api && rm -f data/aergia.test.db && .venv/bin/pytest -q` is green.
- `CustomizePanel.test.tsx` exercises the canonical wire and is unchanged through every subsequent phase.
- The legacy migrator stays; tracked rows in the DB continue to migrate on read until each user re-saves.

## Follow-up

None — the customize panel writes only canonical `Customizations`; the wizard is gone.

## Closeout

Fixed by the canonical `Customizations` wire and covered by `CustomizePanel.test.tsx` plus backend schema/resolver tests; no legacy `colors`/`fonts` payload remains. See `local://phase-7-ast-pipeline-closeout.md`.
