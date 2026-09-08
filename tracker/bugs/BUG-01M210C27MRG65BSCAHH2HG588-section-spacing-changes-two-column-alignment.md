---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M210C27MRG65BSCAHH2HG588
TYPE: bug
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS:
  files:
  - api/app/services/renderer/html.py
  - api/tests/test_html_renderer.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-08T17:17:08.724465+00:00'
UPDATED_AT: '2026-09-08T17:17:08.724465+00:00'
---

# Section spacing changes two-column alignment

## Background

Section spacing controls changed the horizontal date/link rail in two-column sections because field spacing was reused as the grid column gap. The renderer also emitted a default bottom margin after a local Below margin, overriding the user's selection.

## Investigation

`_render_entry_two_column` used `field_gap` for both the vertical stack
inside each column and the grid's horizontal `column-gap`. That moved the
right-hand date/link rail whenever the user changed field spacing. The
section wrapper also appended the template bottom margin after the local
`spacing_after` declaration, so the local value was ignored by the browser.

## Decision

Keep the two-column rail fixed with `column-gap:0`. Apply `field_gap` only
inside the left and right vertical stacks. A local `spacing_after` value owns
the bottom margin; use the template margin only when no local value exists.

## Implementation

- Updated the HTML renderer to separate vertical field rhythm from the
  two-column grid gap and to avoid duplicate bottom-margin declarations.
- Added renderer regression coverage for stable two-column alignment and
  local bottom spacing.

## Verification

- Focused tests: 17 schema, 30 resolver, and 50 renderer tests passed.
- `ruff check app tests`, Python compilation, and `git diff --check` passed.

## Follow-up
