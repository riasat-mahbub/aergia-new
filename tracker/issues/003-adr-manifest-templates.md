---
ID:             003
TYPE:           issue
NAME:           ADR: Manifest-driven templates
SUMMARY:        Why the template system was migrated to a manifest-driven architecture
STATUS:         CLOSED
TAGS:           adr, architecture
---

## Description

### Context

The original template system had two separate pipelines:
1. System templates: hard-coded React components (ModernTemplate, ClassicTemplate, MinimalTemplate)
2. User templates: raw HTML files with `{{zone_id}}` placeholders

This caused code duplication, inconsistent behavior, and made adding new
templates difficult.

### Decision

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
