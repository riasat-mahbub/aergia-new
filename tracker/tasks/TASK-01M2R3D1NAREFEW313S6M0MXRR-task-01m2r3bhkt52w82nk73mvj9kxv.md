---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M2R3D1NAREFEW313S6M0MXRR
TYPE: task
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01M2R3BHKT52W82NK73MVJ9KXV
AFFECTS:
  files:
  - api/app/document_schema/capabilities.py
  - api/app/services/relevance.py
  - api/app/services/rich_text.py
  - api/app/services/renderer/builders/certifications.py
  - web/src/features/builder/domain/customization/fieldsForInstance.ts
  - web/src/shared/cv-editor/section-editors/certifications/CertificationsEditor.tsx
  - web/src/shared/cv/sectionCatalog.ts
  - web/src/shared/cv/sectionData.ts
  - tailoring-skill/skills/aergia-tailor/scripts/validate-candidate.mjs
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-17T16:32:38.570800+00:00'
UPDATED_AT: '2026-09-17T16:32:38.570800+00:00'
---

# Certification descriptions

## Background

Implemented optional rich-text certification descriptions across the editor, document capabilities, AST/HTML renderer, relevance matching, rich-text ID normalization, and tailoring materialization. Legacy certification rows remain compatible and no new section type or migration was needed.

## Investigation

Certifications already had a renderer-backed entry shape and the shared rich-text
renderer. A new section type would duplicate that path without adding a distinct
data model or layout need.

## Decision

Add an optional rich-text `description` to existing certification entries. Keep
the section type, library kind, persisted row shape, and legacy metadata fields
compatible.

## Implementation

The editor, section defaults, capability descriptor, certification builder,
relevance field allowlist, rich-text ID normalizers, and tailoring materializer
now support the field. Empty descriptions are omitted from the AST.

## Verification

Focused renderer/builder/tailoring API tests, the deterministic relevance test,
frontend typecheck/lint/architecture/codegen checks, and all tailoring-skill Node
tests pass. The smoke gate reaches its temporary Alembic migration but that
migration times out in this environment before live server checks.

## Follow-up
