---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M224MYNZ9RM7XZX5JH1A6VJB
TYPE: task
STATUS: IN_PROGRESS
SUMMARY: Add a canonical renderer facade and centralize HTML target values without changing output semantics
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS:
  files:
  - api/app/services/renderer/pipeline.py
  - api/app/services/renderer/html_values.py
  - api/app/services/renderer/builders/__init__.py
  - api/app/services/renderer/tokens.py
  - api/app/services/renderer/resolve.py
  - api/app/services/renderer/html.py
  - api/app/services/renderer/__init__.py
  - api/app/routes/render.py
  - api/app/routes/cvs.py
  - api/app/services/pdf.py
  - api/tests/test_renderer_pipeline.py
  - api/tests/test_smoke_render.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-09T03:51:08.735886+00:00'
UPDATED_AT: '2026-09-09T03:51:08.735886+00:00'
---

# Structural renderer pipeline facade and HTML value centralization

## Background

Introduce a canonical structural render facade and centralize current HTML token/value mappings without changing renderer behavior. Migrate preview, HTML, and PDF callers; defer cascade and capability semantics to follow-up work.

## Investigation

The existing callers independently composed the same AST → resolve → HTML
sequence, and the route/PDF layers each manufactured a CV-like namespace for
the builder. HTML token maps, CSS safety allowlists, link CSS, and print CSS
were split across `tokens.py`, `resolve.py`, and `html.py`.

The repository ADRs establish the HTML-first pipeline as canonical and keep
the resolver pure. A design-pattern review favored a thin Facade/Application
Service over the fixed pipeline, not a stateful orchestrator or a god object.
For token conversion, a target-specific value profile is sufficient while
HTML is the only concrete renderer; a registry or strategy hierarchy would
add indirection without another target to select.

## Decision

Add `RenderSource` and small pipeline functions that normalize wire inputs
once, then compose the existing builder, resolver, HTML renderer, and shared
Chromium runtime. Keep the old stage APIs for focused tests and lower-level
callers.

Move the current HTML token/value tables and sanitizers into
`html_values.py`. Keep `tokens.py` as a compatibility export so the document
schema and existing imports do not change. Preserve all current mapping
values and safety behavior.

## Implementation

* Added `prepare_render_source`, `build_source_document`, `resolve_source`,
  `render_source_html`, and `render_source_pdf`.
* Added `build_document_from_sections` plus named section coercion/build
  helpers; `build_document(cv, manifest)` remains as a compatibility wrapper.
* Migrated `/render/ast`, `/render/html`, `/render/pdf`, CV preview, and
  `PDFService` to the shared facade.
* Moved HTML token maps, CSS value maps, link/print styles, and safety helpers
  into the HTML value profile.
* Updated the end-to-end smoke test to exercise the facade and added a small
  facade boundary test.

## Verification

* `ruff check` on changed renderer, route, service, and test files: passed.
* Focused renderer tests: `123 passed`.
* CV/link route regressions: `11 passed`.
* Chromium PDF smoke: `1 passed` outside the restricted sandbox.
* Old and new composed HTML for the full smoke fixture were byte-for-byte
  identical (`8806` bytes).

## Follow-up

Keep the known functional issues separate from this structural slice:

* Pydantic default-valued partial overrides still need an explicit patch
  representation before cascade semantics can be corrected.
* Skills `skill_variant` and the support vocabulary need a deliberate semantic
  decision before layout behavior changes.
* The large HTML renderer still contains layout/markup sub-functions and
  regex-based metadata surgery; split those in a later behavior-preserving
  pass after the new facade is observed in use.
