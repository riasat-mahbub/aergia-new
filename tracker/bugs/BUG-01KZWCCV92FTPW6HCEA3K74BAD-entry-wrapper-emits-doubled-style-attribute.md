---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KZWCCV92FTPW6HCEA3K74BAD
TYPE: bug
STATUS: DONE
PRIORITY: Medium
SEVERITY: Medium
EFFORT: XS
OWNER: riasat
CONFIDENCE: High
TAGS:
- renderer
- bug
RELATIONS: null
AFFECTS:
  files:
    - api/app/services/renderer/html.py
LINKS:
  plan: local://legacy-look-preservation-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-13T01:39:41.474625+00:00'
UPDATED_AT: '2026-08-13T01:40:00+00:00'
---

# Entry wrapper emits doubled style= attribute

## Background

Every section's first entry wrapper rendered with two `style=` attributes:

```
<div class="entry" style="break-before:avoid; style="display:flex;flex-direction:column;gap:var(--spacing-subsection, 16px);">
```

The HTML parser picks the first attribute and ignores the second, which silently dropped the entry's own flex layout declarations (`display:flex;flex-direction:column;gap:...`). The first entry of every section lost its `display:flex` layout in the parsed DOM.

## Investigation

Confirmed in rendered HTML at `/tmp/current_modern.html`, `/tmp/current_classic.html`, `/tmp/current_minimal.html`. The renderer emitted this for every section whose `heading_keeps_with_first` was truthy (the default for all section types per `LayoutHints.heading_keeps_with_first = True` at `models.py:138`).

The root cause was `_render_section` in `api/app/services/renderer/html.py` at lines 277-286 (pre-fix):

```python
entry_html = entry_html.replace(
    '<div class="entry"',
    f'<div class="entry" style="{keep_first};',
    1,
)
```

The string-replace prepended a new `style=` attribute rather than merging into the existing one. The HTML5 spec says only the first attribute wins on duplicates.

## Decision

Replace the string-replace with a regex-merge helper that folds the `break-before:avoid` declaration into the entry's existing `style` attribute. Single `style=` attribute, correct parsed layout, no change in behavior for entries without a prior `style=` (they get one).

## Implementation

- `api/app/services/renderer/html.py`: added `_ENTRY_OPEN_RE` and `_merge_entry_break_before` helper; updated `_render_section` to call the helper.
- Helper regex matches `<div class="entry"` optionally followed by ` style="..."`, captures the existing declarations, appends `break-before:avoid` if missing, joins with `_format_inline_style`, emits a single attribute.
- Test `api/tests/test_html_renderer.py:269` (`.f-link::after` assertion) is **not** touched here — that lands in Step 4.

## Verification

- Pytest: `tests/test_html_renderer.py` and `tests/test_resolve.py` — 43 passed, 0 failed.
- Rendered HTML grep: `grep -oE '<[^>]*style="[^"]*"[^>]*style="[^"]*"[^>]*>' /tmp/current_*.html` returned zero matches. The bug is gone.
- Per-section first-entry wrapper now reads `<div class="entry" style="display:flex;flex-direction:column;gap:var(--spacing-subsection, 16px);break-before:avoid">` — single attribute, both declarations preserved.

## Follow-up

None. Step 1 of `local://legacy-look-preservation-plan.md` is closed.
