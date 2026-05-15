---
ID:             011
TYPE:           feature
NAME:           Manifest-driven template pipeline
SUMMARY:        Single manifest JSON schema unifying system and user templates
STATUS:         CLOSED
TAGS:           manifest, templates, phase-2
LINKS:          phase=PLAN.md-phase-2
---

## Description

Replaced the dual-pipeline template system with a single manifest-driven approach:
- Every template defined by 4 artefacts: `manifest.json`, `template.html`,
  `styles.css`, optional assets
- Manifest Pydantic model + JSON Schema validation
- Alembic migration adding `manifest` and `assets` JSONB columns
- `POST /templates` multipart endpoint with manifest validation + HTML generation
- `GET /templates/{id}/manifest` and `GET /templates/{id}/html` endpoints
- Seed script converts 3 existing system templates to manifest rows
- Legacy columns kept for backward compatibility

## Status

Phase 2 complete. Task 2.7 (integration tests) pending.
