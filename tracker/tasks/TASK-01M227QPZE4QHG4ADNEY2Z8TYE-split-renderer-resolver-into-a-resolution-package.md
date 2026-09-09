---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M227QPZE4QHG4ADNEY2Z8TYE
TYPE: task
STATUS: IN_PROGRESS
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS:
  files:
  - api/app/services/renderer/resolve.py
  - api/app/services/renderer/resolution/__init__.py
  - api/app/services/renderer/resolution/context.py
  - api/app/services/renderer/resolution/errors.py
  - api/app/services/renderer/resolution/render_model.py
  - api/app/services/renderer/resolution/sections.py
  - api/app/services/renderer/resolution/zones.py
  - api/app/services/renderer/pipeline.py
  - api/tests/test_resolve.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-09T04:45:04.878233+00:00'
UPDATED_AT: '2026-09-09T04:45:04.878233+00:00'
---

# Split renderer resolver into a resolution package

## Background

Behavior-preserving refactor of api/app/services/renderer/resolve.py into a resolution package with a compatibility facade. Extract typed context, section cascade, zone resolution, and RenderModel assembly; preserve public imports and output semantics.

## Investigation

`resolve.py` mixed four responsibilities: compatibility-boundary coercion,
per-section style cascading, zone placement/token conversion, and final
`RenderModel` assembly. Its tests also imported `_resolve_zone_styles` and
`_overlay_policy` directly, which made private implementation structure part
of the test contract.

The existing precedence and capability behavior is intentional. In
particular, an AST section policy must survive resolution when present; the
resolver only calls `resolve_policy` for sections without a policy. The
renderer package already has a canonical pipeline, so the resolver can expose
a typed core for that pipeline while retaining a wire-input facade for older
callers.

## Decision

Create a small `renderer/resolution/` package with one typed
`ResolutionContext`, separate section, zone, and render-model stages, and a
`resolve_validated(document, context)` entrypoint. Keep `resolve.py` as a
compatibility facade that validates dict inputs and delegates to the typed
core. Migrate the canonical pipeline to the typed entrypoint so prepared
sources are not coerced a second time.

Test zone token conversion and policy overlay through public document
resolution rather than preserving compatibility exports for private helpers.
This keeps tests focused on observable resolver contracts while allowing the
internal stages to be reorganized later.

## Implementation

* Added `ResolutionContext` plus manifest/customization coercion at the
  compatibility boundary.
* Moved section precedence, per-instance overlays, policy defaults, and
  capability gates to `resolution/sections.py`.
* Moved zone placement and HTML token conversion to `resolution/zones.py`.
* Moved CSS-variable and `RenderModel` assembly to
  `resolution/render_model.py`.
* Reduced `resolve.py` to the stable public facade and moved the canonical
  pipeline to `resolve_validated`.
* Rewrote zone and policy tests to exercise `resolve()` instead of importing
  `_resolve_zone_styles` or `_overlay_policy`.

## Verification

* Ruff checks for the changed resolver, pipeline, and tests: passed.
* Renderer package compile check: passed.
* Manual execution of the 131 renderer/builder/resolver test functions:
  passed.
* Direct resolver, pipeline, and compatibility-boundary smoke checks: passed.
* The normal pytest command was attempted, but the repository's existing
  `tests/conftest.py` stalled while running its Alembic test-database setup
  before test collection; no resolver failure was reported.

## Follow-up

None for this structural slice. Keep future functional cascade changes
separate from this package move.
