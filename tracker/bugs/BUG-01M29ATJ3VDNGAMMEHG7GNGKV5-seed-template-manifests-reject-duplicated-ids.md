---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M29ATJ3VDNGAMMEHG7GNGKV5
TYPE: bug
STATUS: DONE
PRIORITY: null
SEVERITY: Medium
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS:
- templates
- manifest
- startup
RELATIONS: null
AFFECTS:
  files:
  - api/app/db/seed.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-11T22:53:44.955730+00:00'
UPDATED_AT: '2026-09-11T22:53:44.955730+00:00'
---

# Seed template manifests reject duplicated IDs

## Background

Application startup fails because the built-in v2 seed manifests include an id field that TemplateManifest rejects as an extra input.

## Investigation

``TemplateManifest`` is intentionally closed with ``extra="forbid"`` and
does not define an ``id`` field. The database template row already owns the
template ID in ``SEED_TEMPLATES[*]["id"]``; the nested manifest copies were
therefore invalid duplicate metadata.

## Decision

Keep template identity on the database row and preserve the v2 manifest
schema unchanged.

## Implementation

Removed the duplicated ``id`` key from the modern, classic, and minimal seed
manifest payloads.

## Verification

All three seed manifests validate with ``TemplateManifest``. The focused seed
tests pass (10 passed, 1 deselected); Ruff and ``git diff --check`` also pass.
The full fixture-backed template test command could not complete in this
environment because a fresh ``aiosqlite`` connection hangs before collection.

## Follow-up
