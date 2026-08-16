---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNCD
TYPE: task
STATUS: PLANNED
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- plan
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T19:21:18.630193+00:00'
UPDATED_AT: '2026-08-01T19:21:18.630193+00:00'
---

# Frontend defense-in-depth: renderManifest carries zones

## Background

Modify web/src/components/preview/UserTemplateRenderer.tsx so renderManifest also carries zones at top level matching layout_config.zones, mirroring render_preview. Verify: cd web && npm run build (tsc -b && vite build). Expect: build succeeds.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KYZCC3H6YG1FC1WCXH3NNRFY during the schema-4 cutover. -->
