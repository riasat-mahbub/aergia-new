---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KZPHASE6STEP1-DELETE
TYPE: task
STATUS: PROPOSED
SUMMARY: 'Delete TemplateWizard, TemplateCreatorPage, BaseTemplateCard, TemplateLayoutView, userTemplateStore and their tests.'
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: riasat
CONFIDENCE: High
TAGS:
- phase-6
- deletion
RELATIONS:
  part_of:
    - FEAT-01KZPHASE6STEP1
  supersedes:
    - BUG-01KZJ0PHASE2QA-template-wizard-on-legacy-paths
AFFECTS:
  files:
    - web/src/components/template-creator/TemplateWizard.tsx
    - web/src/components/template-creator/BaseTemplateCard.tsx
    - web/src/components/template-creator/TemplateLayoutView.tsx
    - web/src/components/template-creator/__tests__/TemplateWizard.test.tsx
    - web/src/components/template-creator/__tests__/BaseTemplateCard.test.tsx
    - web/src/components/template-creator/__tests__/TemplateLayoutView.test.tsx
    - web/src/pages/TemplateCreatorPage.tsx
    - web/src/lib/store/userTemplateStore.ts
    - web/src/main.tsx
    - web/src/components/common/AppLayout.tsx
LINKS:
  plan: local://phase-6-content-only-authoring-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: 2026-08-08
UPDATED_AT: 2026-08-08
---

# Delete the template-authoring surface

## Background

After Phase 4 + Phase 5 the template-authoring wizard authors templates in a
vocabulary that is no longer open; the customize panel already exposes every
styling decision the closed vocabulary allows. Keeping the wizard alive
creates two competing authoring paths and is the only remaining cause of
legacy drift.

## Decision

Clean cutover with no shims:
- Delete `TemplateWizard.tsx`, `BaseTemplateCard.tsx`, `TemplateLayoutView.tsx`
  and their `__tests__/` files.
- Delete `TemplateCreatorPage.tsx` (sole host of the wizard).
- Delete `userTemplateStore.ts` (backed only by the modal's user-templates
  section).
- Delete the empty `web/src/components/template-creator/` directory.
- Remove the `<Route path="template-creator">` entry in `main.tsx`.
- Remove the `LayoutTemplate` nav link in `AppLayout.tsx`.

## Implementation

Plan §3 + §4.6 + §4.7 + §4.8. Verify with:

```bash
grep -rn "TemplateWizard\|TemplateCreatorPage\|template-creator\|BaseTemplateCard\|TemplateLayoutView\|userTemplateStore" web/src api/
# expect: zero matches
```

## Verification

Frontend `npm run build` must succeed. `npm run test` must pass (168 + tests,
the 12 `node_modules_bak/zod` failures are pre-existing and unrelated).

## Follow-up

None — this is the cutover.
