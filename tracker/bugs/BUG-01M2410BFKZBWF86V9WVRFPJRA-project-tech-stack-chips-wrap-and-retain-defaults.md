---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M2410BFKZBWF86V9WVRFPJRA
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: Medium
EFFORT: S
OWNER: riasat
CONFIDENCE: Medium
TAGS:
- renderer
- chips
- projects
RELATIONS:
  related:
  - FEAT-01M129QBNK54QF2Y9PV8WDKNA0
AFFECTS:
  files:
  - api/app/services/renderer/builders/__init__.py
  - api/app/services/renderer/html_renderer/html_entries.py
  - api/app/services/renderer/html_renderer/html_document.py
  - api/tests/test_builders.py
  - api/tests/test_html_renderer.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-09T21:25:56.851904+00:00'
UPDATED_AT: '2026-09-09T21:25:56.851904+00:00'
---

# Project tech-stack chips wrap and retain defaults

## Background

Project tech-stack fields were emitted as direct flex-column children, stretching each chip to the full left column and stacking them. Partial project layout overrides also replaced the type default and dropped chip_keys. Group repeated chip fields in a wrapping renderer row, use rounded pill styling, and merge explicit layout values over project defaults while preserving explicit chip opt-outs.

## Investigation

The project builder already emits one ``tech`` ``FieldBlock`` per stored
technology, and the project type default already identifies ``tech`` as a
chip field. In the two-column layout those spans were direct children of a
column flex container, so Chromium stretched and stacked them. A partial
``LayoutHints`` override was also validated without seeding the project type
default, causing ``chip_keys`` to become ``None``.

## Decision

Keep repeated values as separate AST fields and group them only in the HTML
renderer. Use a generic wrapping chip group so the renderer remains keyed by
``LayoutHints.chip_keys`` rather than by section type. Seed type defaults before
overlaying explicit layout fields; an explicit empty or null ``chip_keys``
continues to opt out.

## Implementation

Added ``f-chip-group`` wrappers for consecutive chip fields in stack and
two-column entry paths. Updated chips to use inline-flex pill styling with
wrapping, spacing, long-label bounds, and non-underlined chip links. Added
``_merge_layout_defaults`` to preserve project chips through partial layout
overrides.

## Verification

The focused builders and HTML renderer suite passes (98 tests), Ruff passes
for all changed Python files, and a read-only Chromium geometry check confirms
chips have content-sized widths and wrap horizontally inside the left column.

## Follow-up

The full pytest setup could not be run in this environment because its
temporary aiosqlite migration connection hangs before test collection; the
pure renderer/builders tests were run with the database fixture disabled.
