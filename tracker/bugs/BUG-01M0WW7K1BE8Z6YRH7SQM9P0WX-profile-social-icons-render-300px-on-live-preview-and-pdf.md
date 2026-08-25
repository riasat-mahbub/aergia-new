---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M0WW7K1BE8Z6YRH7SQM9P0WX
TYPE: bug
STATUS: PROPOSED
PRIORITY: High
SEVERITY: null
EFFORT: XS
OWNER: riasat
CONFIDENCE: High
TAGS:
- renderer
- css
- regression
RELATIONS: null
AFFECTS:
  files:
    - api/app/services/renderer/html.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-25T16:32:08.235721+00:00'
UPDATED_AT: '2026-08-25T16:32:08.235721+00:00'
---

# Profile social icons render ~300px on live preview and PDF

## Background

User reported the profile social icons had suddenly become huge on both the
live preview iframe and the PDF export. This affected every template since
the icons are emitted by the shared HTML renderer (`HTMLDocumentRenderer`)
and the iframe preview posts to the same `/render/html` endpoint.

## Investigation

Inspected `api/app/services/renderer/html.py`. The renderer emits each
social link icon as:

```html
<span class="f-icon" aria-hidden="true">
  <svg viewBox="0 0 24 24" fill="currentColor"><path .../></svg>
</span>
```

The document CSS ships only:

```css
.f-icon svg { width:100%; height:100%; }
```

No width/height is set on `.f-icon` itself, and the SVG has no intrinsic
size (just a `viewBox`, no `width`/`height` attrs). A sized-by-parent
inline SVG with no parent size collapses to the CSS default of ~300x150 px
for replaced elements without intrinsic dimensions.

Reproduction (Playwright Chromium headless against the rendered HTML):

| Metric          | Before fix      | After fix |
|-----------------|-----------------|-----------|
| `.f-icon svg` BBox | 344.06 x 344.06 px | 9.95 x 9.95 px |
| `.f-icon svg` computed size | 344.062px | ~0.75em |

`git diff master -- api/app/services/renderer/html.py` confirms the
working tree had dropped the wrapper rule:

```diff
-    .f-icon { display:inline-flex; width:0.75em; height:0.75em;
-              margin-right:0.25em; vertical-align:-0.1em; }
     .f-icon svg { width:100%; height:100%; }
```

The wrapper rule was added in commit `2f50246` and last tweaked in
`920a5fc` (smaller 0.75em). It never had a regression-causing change on
master — it was lost in the user's uncommitted working tree.

## Decision

Restore the wrapper rule verbatim from the last green state. No CSS
token or design change — purely restoring the rule the renderer was
designed to rely on. The CSS is the only thing that prevents the icon
SVG from claiming the entire available width.

## Implementation

One-line restore in `api/app/services/renderer/html.py` inside
`_render_document`'s `<style>` block, immediately above the existing
`.f-icon svg` rule:

```css
.f-icon { display:inline-flex; width:0.75em; height:0.75em;
          margin-right:0.25em; vertical-align:-0.1em; }
.f-icon svg { width:100%; height:100%; }
```

## Verification

- `cd api && pytest tests/test_builders.py tests/test_html_renderer.py tests/test_render_links.py tests/test_smoke_render.py -q`
  -> 77 passed, 0 failed.
- Playwright Chromium BBox of `.f-icon svg` against a rendered profile
  with `github` + `linkedin` social links: 9.95 x 9.95 px (was
  344 x 344 px). Both preview iframe and PDF export use the same HTML
  so the fix applies to both.

## Follow-up

None. The wrapper rule has always been load-bearing for the icon sizing.
Consider adding a regression test that asserts the rendered document CSS
contains the `.f-icon` wrapper rule so this can't regress silently.