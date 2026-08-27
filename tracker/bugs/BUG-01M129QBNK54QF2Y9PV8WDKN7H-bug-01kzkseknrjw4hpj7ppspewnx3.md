---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M129QBNK54QF2Y9PV8WDKN7H
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01M129QBNK54QF2Y9PV8WDKN7E
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T17:34:53.389904+00:00'
UPDATED_AT: '2026-08-09T17:34:53.389904+00:00'
---

# BUG-01KZKSEKNRJW4HPJ7PPSPEWNX3

## Background

Fixed: Customizations gained a layout: CVLayout field (zones+placement); resolve._resolve_zones merges customizations.layout over manifest zones and matches placement by section id or type; create_cv installs the template zones into a new CV's layout; UserTemplateRenderer sends cv_sections + layout via customizations and never fabricates a manifest-less payload. Verified: new CV opens with zones, preview renders CV content, template switch has no 422. Tests: test_cv_creation_installs_template_zones, test_resolve_uses_customizations_layout_over_manifest, test_resolve_placement_matches_instance_id_before_type, test_customizations_accepts_layout, UserTemplateRenderer.test.tsx (4).

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from BUG-01KZKSEZYDT8MQA88BNK71PZM4 during the schema-4 cutover. -->
