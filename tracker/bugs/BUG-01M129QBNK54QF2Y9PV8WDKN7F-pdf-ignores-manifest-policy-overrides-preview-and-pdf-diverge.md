---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M129QBNK54QF2Y9PV8WDKN7F
TYPE: bug
STATUS: PROPOSED
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T17:34:45.958390+00:00'
UPDATED_AT: '2026-08-09T17:34:45.958390+00:00'
---

# PDF ignores manifest policy_overrides (preview and PDF diverge)

## Background

export_pdf and /cvs/{id}/preview called build_document(cv, None); the live preview (/render/html) passes the manifest. build_document resolves per-type policy from the manifest when given, so template policy_overrides (e.g. skills inline) applied in the preview but were silently lost in the PDF. Fix: pass the validated manifest to build_document in both PDF and preview paths.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from BUG-01KZKSERP6P868SCQMXGE2QMWQ during the schema-4 cutover. -->
