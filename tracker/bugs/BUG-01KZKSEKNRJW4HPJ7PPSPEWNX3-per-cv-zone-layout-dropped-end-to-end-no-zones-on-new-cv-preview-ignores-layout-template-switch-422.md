---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KZKSEKNRJW4HPJ7PPSPEWNX3
TYPE: bug
STATUS: PROPOSED
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T17:34:40.824331+00:00'
UPDATED_AT: '2026-08-09T17:34:40.824331+00:00'
---

# Per-CV zone layout dropped end-to-end (no zones on new CV, preview ignores layout, template switch 422)

## Background

The Customizations schema had no layout field, so the editor's customizations.layout bag was silently dropped at every save; resolve() read zones only from the manifest; the preview injected a legacy layout_config key into the v2 manifest (dead code) and sent cv_data.instances instead of cv_sections, so the UI preview never rendered CV content. create_cv stored customizations as given, so new CVs had zero zones. Template switch hit 'TemplateManifest name Field required' when templateManifest was null during refetch.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
