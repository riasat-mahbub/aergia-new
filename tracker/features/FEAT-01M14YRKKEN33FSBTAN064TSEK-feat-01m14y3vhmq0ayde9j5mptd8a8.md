---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M14YRKKEN33FSBTAN064TSEK
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: riasat
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M14Y3VHMQ0AYDE9J5MPTD8A8
AFFECTS:
  files:
  - README.md
  - api/app/db/seed.py
  - api/app/schema/models.py
  - api/app/schemas/cv.py
  - api/app/services/application.py
  - api/app/services/renderer/builders/__init__.py
  - api/app/services/renderer/builders/_utils.py
  - api/app/services/renderer/html.py
  - api/app/services/renderer/policy.py
  - api/app/services/renderer/resolve.py
  - api/app/services/renderer/tokens.py
  - web/src/components/cv-list/CreateCvModal.tsx
  - web/src/components/cv-list/ImportCvModal.tsx
  - web/src/components/sections/skills/SkillsEditor.tsx
  - web/src/lib/sections/DateField.tsx
  - web/src/lib/sections/styleDefaults.ts
  - web/src/generated/schema.ts
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-28T19:50:18.478092+00:00'
UPDATED_AT: '2026-08-28T19:50:18.478092+00:00'
---

# FEAT-01M14Y3VHMQ0AYDE9J5MPTD8A8

## Background

Implemented default CV generation preferences: generic-minimal for new/imported/application-generated CVs, none spacing token, Month YYYY date fallback, underlined section headings, smallest default rich-text CSS, and accessible per-skill removal. Added renderer fallback coverage, schema/codegen updates, and frontend/backend regression tests. Focused backend: 161 passed; frontend: 339 passed; build/codegen/Ruff green.

## Investigation

The default-template path existed in the API, create modal, and PDF import flow,
but each used `generic-modern`. The application fit loop already used
`generic-minimal` but still requested the old `minimal` spacing token. Date
formatting happens in builders before resolution, so changing only the
resolver fallback did not change generated date text. Skill groups already
supported per-item deletion in the editor; the control lacked explicit button
semantics and coverage.

## Decision

Use `generic-minimal` and an explicit `none` spacing token for generated and
new default CVs. Make `Month YYYY` the schema/builder fallback, keep explicit
date overrides intact, default visible section dividers to enabled, and keep
the existing editable skill-group model with per-item removal.

## Implementation

Added the `none` spacing token and renderer mapping, updated API/frontend
defaults and seed manifest, applied smallest default CSS sizing to rich-text
summary/description fields, resolved date defaults before date-bearing
builders run, fixed policy merging for explicit divider overrides, regenerated
TypeScript schema output, and added accessible skill-chip removal.

## Verification

Focused backend suite: 203 passed on a fresh database. Frontend suite: 339
passed. Production build, codegen drift check, Ruff, and `git diff --check`
passed. Full backend suite: 446 passed and 4 unrelated pre-existing failures
in asset/auth contracts under the current environment; full frontend lint
retains the repository's existing `no-explicit-any` errors.

## Follow-up

Consider trimming individual skill items during deterministic fit passes,
adding language rows to application generation, and introducing application
CV revisions/provenance and follow-up events.
