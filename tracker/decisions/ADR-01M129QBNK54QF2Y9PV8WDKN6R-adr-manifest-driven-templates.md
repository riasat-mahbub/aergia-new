---
SCHEMA: 4
FORMAT: project-tracker
ID: ADR-01M129QBNK54QF2Y9PV8WDKN6R
TYPE: adr
STATUS: DONE
SUMMARY: Why the template system was migrated to a manifest-driven architecture
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- adr
- architecture
RELATIONS:
  related:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN8A
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:18:34.333019+00:00'
UPDATED_AT: '2026-08-01T16:18:34.333019+00:00'
---

# ADR: Manifest-driven templates

## Background

Why the template system was migrated to a manifest-driven architecture

The original template system had two separate pipelines:
1. System templates: hard-coded React components (ModernTemplate, ClassicTemplate, MinimalTemplate)
2. User templates: raw HTML files with `{{zone_id}}` placeholders

This caused code duplication, inconsistent behavior, and made adding new
templates difficult.

*Migrated from SCHEMA 2 entry 003-adr-manifest-templates.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision

Unify both pipelines under a single manifest JSON schema. Every template
is defined by 4 artefacts: `manifest.json`, `template.html`, `styles.css`,
optional assets. The visual editor writes the manifest; HTML/CSS are
derived from it. The renderer operates on the manifest alone.

### Consequences

- Single render path for all templates
- System templates are just seeded manifest rows with `is_system=true`
- New template format is self-describing (schema lives in the manifest)
- Migration required DB schema changes (JSONB columns) and API endpoint rewrites

### Date

2026-05-01 (Phase 2)

## Implementation


## Verification


## Follow-up

<!-- Migrated from ADR-01KYZ1XG6W0K8NQPMV2Z6WCVYM during the schema-4 cutover. -->
