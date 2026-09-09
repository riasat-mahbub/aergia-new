---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M23FK4M3R0RSBYQ1ZWQ6PGCE
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  depends_on:
  - TASK-01M225JTBDSM6S7HE9EA9S1Q4B
AFFECTS:
  files:
  - api/app/services/renderer/html.py
  - api/app/services/renderer/html_assets.py
  - api/app/services/renderer/html_markup.py
  - api/app/services/renderer/html_fields.py
  - api/app/services/renderer/html_entries.py
  - api/app/services/renderer/html_sections.py
  - api/app/services/renderer/html_document.py
  - api/tests/test_html_renderer.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-09T16:21:38.051122+00:00'
UPDATED_AT: '2026-09-09T16:21:38.051122+00:00'
---

# Split HTML renderer into focused modules

## Background

Extract the HTML renderer's static assets, markup escaping/style helpers, field rendering, entry rendering, section rendering, and document assembly into focused modules while retaining the app.services.renderer.html facade and exact output behavior.

## Investigation

The renderer facade had accumulated static SVG assets, escaping and CSS
serialization, field and rich-text rendering, entry layout logic, section
layout, and complete-document assembly in one 1,022-line module. The public
class was already a thin boundary, so these concerns could be moved without
changing the renderer protocol or callers.

## Decision

Keep ``app.services.renderer.html`` as the stable import path and retain
``HTMLDocumentRenderer`` as the only public renderer class. Organize the
implementation by rendering responsibility, with the facade delegating to a
private document assembly function. Preserve the existing regex metadata
helpers and all HTML strings in this pass; changing their semantics is a
separate follow-up.

## Implementation

Added focused modules for social SVG assets, markup helpers, field/rich-text
rendering, entry layouts, section rendering, and document/stylesheet assembly.
Reduced ``html.py`` to the capability-declaring facade and added a deterministic
SHA-256 characterization test for a reference ``RenderModel``.

## Verification

* The characterization output remains byte-for-byte stable (5,795 bytes;
  SHA-256 ``dbdc6ad028b35e528b205f7fe25adca3baae0a8e657f9156937ff06bdb350abc``).
* 124 synchronous renderer, resolver, builder, and pipeline tests pass when
  invoked without the repository's DB fixture setup.
* Ruff checks, Python compilation, and extracted-module imports pass.
* The frontend build/lint portions of ``./dev.sh --smoke`` pass. The live-stack
  portion reaches the known Alembic async-SQLite migration timeout before
  exercising the renderer.

## Follow-up

The regex-based entry metadata surgery remains intentionally unchanged and can
be isolated or replaced in a later behavior-preserving task.
