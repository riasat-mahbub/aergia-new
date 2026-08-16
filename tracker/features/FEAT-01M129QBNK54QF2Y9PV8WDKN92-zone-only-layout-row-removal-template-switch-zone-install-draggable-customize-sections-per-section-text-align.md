---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN92
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- layout
- zones
- text-align
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-02T00:05:43.767934+00:00'
UPDATED_AT: '2026-08-02T00:05:43.767934+00:00'
---

# Zone-only layout: row removal, template-switch zone install, draggable customize sections, per-section text align

## Background

Removed the legacy row model end to end (RowIR flattened to DocumentIR.zones, _format_row deleted, row/rowHeights stripped from seed manifests, ZoneManifest.row dropped, BaseTemplateCard flattened, wizard copy updated) and fixed four post-zone-only gaps: (1) handleTemplateChange now fetches the new template and installs its zones, reassigning every section to the first zone; (2) SectionZoneView rows are now the drag target (listeners on the row div, grip button and dead eye toggle removed, onToggle chain dropped, CustomizePanel readOnly=false); (3) SectionStyle gained text_align reaching heading+body via the panel wrapper, profile renders text-align:center by default and explicit overrides win (BuilderPage.handleUpdateStyle keeps text_align-only styles); (4) TemplateDetail exposes derived layout_config and create_cv seeds layout from the template manifest. DB wiped; templates re-seeded row-free. Backend tests 26 pass; frontend 1906 pass (2 pre-existing TemplateSwitcher iframe failures, identical at baseline); tsc + vite build green; grep sweep for row symbols clean (only sanctioned RowIR alias + negative test assertions); full e2e API smoke and browser UI smoke passed.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from FEAT-01KYZWMWPQN3NGH2V4K2YWPVFZ during the schema-4 cutover. -->
