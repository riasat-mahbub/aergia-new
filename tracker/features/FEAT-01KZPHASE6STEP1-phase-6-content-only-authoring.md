---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KZPHASE6STEP1
TYPE: feature
STATUS: IN_PROGRESS
SUMMARY: 'Delete the user-facing template-authoring surface; the customize panel is the sole styling surface.'
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: riasat
CONFIDENCE: High
TAGS:
- phase-6
- template-authoring
- content-only
RELATIONS:
  part_of:
    - EPIC-01KZCCC3MTXDGPY31H06NFYP1Q
  supersedes:
    - FEAT-01KYZ1HCS9ZKCJ9NDHXZP1SA9K
AFFECTS:
  files:
    - web/src/components/template-creator/TemplateWizard.tsx
    - web/src/components/template-creator/BaseTemplateCard.tsx
    - web/src/components/template-creator/TemplateLayoutView.tsx
    - web/src/pages/TemplateCreatorPage.tsx
    - web/src/lib/store/userTemplateStore.ts
    - web/src/components/customization/TemplateSelectorModal.tsx
    - web/src/lib/api/templates.ts
    - web/src/main.tsx
    - web/src/components/common/AppLayout.tsx
    - api/app/routes/templates.py
    - api/app/schema/models.py
    - api/app/schema/__init__.py
    - api/app/models/template.py
    - api/app/models/user.py
    - api/app/db/seed.py
    - api/scripts/codegen_schema.py
    - api/alembic/versions/
    - api/tests/test_templates.py
LINKS:
  plan: local://phase-6-content-only-authoring-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: 2026-08-08
UPDATED_AT: 2026-08-08
---

# Phase 6 step 1 — Content-only authoring

## Background

Phase 4 closed the manifest's design vocabulary to typed tokens; Phase 5 cut
the resolver away from the concrete `HTMLDocumentRenderer`. With both done,
the user-facing template-authoring surface (the wizard, the
`/api/v1/templates/user` routes, the user-templates section of
`TemplateSelectorModal`, the multipart `/api/v1/templates` upload) is
redundant: it authored templates in a vocabulary that is no longer open, and
the customize panel already exposes every styling decision the closed
vocabulary allows.

## Investigation

Scope confirmed by reading the existing surfaces:
- `web/src/components/template-creator/` — wizard, picker cards, layout view.
- `api/app/routes/templates.py` — three user-template endpoints and one
  multipart upload endpoint. `create_template_from_manifest` has zero frontend
  consumers (the wizard's `uploadUserTemplate` calls `POST /templates/user`).
- `web/src/components/customization/TemplateSelectorModal.tsx` — split between
  system-template list, user-template list, and file upload.
- `api/app/models/template.py` — `is_system` and `user_id` columns become
  vestigial once user-template authoring is removed.

The customize panel already owns the three-axis wire shape (Layout /
Subsection / Policy / Field-styles), the Document disclosure (accent /
body-font / heading-font / spacing), and `RendererSupport`-gated control
visibility. No new control surface is needed.

## Decision

Delete the authoring surface entirely. After this phase:
- A CV can only be customised through the customize panel.
- All styling flows through `Customizations`.
- The resolve step has a single source of styling truth per CV.
- The renderer stack sees no schema-shape changes.
- The DOCX renderer (Phase 6 step 4) becomes a renderer-only change because
  no authoring surface depends on manifest shape.

Existing CVs whose `template_id` references a deleted `user_*` template fall
back to `generic-modern` on next open. The brief's "user-templates routes
and DB tables" wording is read as "the user-templates surface"; preserving
user templates is out of scope.

## Implementation

See `local://phase-6-content-only-authoring-plan.md` for the full plan. Track
work via the four task entries registered under this feature.

## Verification

```bash
grep -rn "TemplateWizard\|TemplateCreatorPage\|template-creator\|BaseTemplateCard\|TemplateLayoutView\|userTemplateStore" web/src api/
grep -rn "create_user_template\|delete_user_template\|list_user_templates\|create_template_from_manifest\|UserTemplateCreate" api/
grep -rn "uploadUserTemplate\|deleteUserTemplate\|fetchUserTemplates\|is_user_template" web/src/
cd api && pytest -q && ruff check .
cd web && npm run build && npm run lint && npm test
python api/scripts/codegen_schema.py --check
```

## Follow-up

Phase 6 steps 2–7 (drag-drop zone authoring, multi-template preview, per-entry
policy overrides, DOCX renderer, asset upload UI, DOCX parity verification).
