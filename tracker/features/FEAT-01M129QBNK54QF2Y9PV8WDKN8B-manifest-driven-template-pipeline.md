---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN8B
TYPE: feature
STATUS: DONE
SUMMARY: Single manifest JSON schema unifying system and user templates
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- manifest
- templates
- phase-2
RELATIONS:
  implements:
  - ADR-01M129QBNK54QF2Y9PV8WDKN6R
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:11:57.689134+00:00'
UPDATED_AT: '2026-08-01T16:11:57.689134+00:00'
---

# Manifest-driven template pipeline

## Background

Single manifest JSON schema unifying system and user templates

Replaced the dual-pipeline template system with a single manifest-driven approach:
- Every template defined by 4 artefacts: `manifest.json`, `template.html`,
  `styles.css`, optional assets
- Manifest Pydantic model + JSON Schema validation
- Alembic migration adding `manifest` and `assets` JSONB columns
- `POST /templates` multipart endpoint with manifest validation + HTML generation
- `GET /templates/{id}/manifest` and `GET /templates/{id}/html` endpoints
- Seed script converts 3 existing system templates to manifest rows
- Legacy columns kept for backward compatibility

*Migrated from SCHEMA 2 entry 011-manifest-pipeline.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification

Phase 2 complete. Task 2.7 (integration tests) pending.

## Follow-up

<!-- Migrated from FEAT-01KYZ1HCVSDJN5FRA0R4AY3VR4 during the schema-4 cutover. -->
