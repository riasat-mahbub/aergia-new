---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KZWCX2ZSPSHKWD5E0TB0EFXM
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: riasat
CONFIDENCE: High
TAGS:
- renderer
- links
- skills
- chips
- legacy-look
RELATIONS:
  supersedes:
  - FEAT-01KZ708J2NVNK63N0R4QHX7ZGM-skills-section-inline-layout-variant
AFFECTS:
  files:
    - api/app/services/renderer/html.py
    - api/app/schema/models.py
    - api/app/services/renderer/builders/__init__.py
    - api/app/services/renderer/tokens.py
    - api/tests/test_html_renderer.py
    - api/tests/test_resolve.py
LINKS:
  plan: local://legacy-look-preservation-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-13T02:10:00+00:00'
UPDATED_AT: '2026-08-13T02:10:00+00:00'
---

# Inline link arrow, chip pills, skills inline layout

## Background

Three related renderer behaviors that drifted or were lost in the AST cutover:

1. **Link arrow as `::after` pseudo-element.** The trailing `↗` is rendered via `.f-link::after { content: " ↗"; }`. This is not part of the link's text content, so it is not selectable, not part of Chromium's PDF text extraction, and not underlined along with the link. Legacy used an inline `<span aria-hidden="true"> ↗</span>` so the arrow was a real text node.
2. **Tech chip pills.** Legacy `projects` rendered `tech_stack` items as blue pill spans (`background:#eff6ff; color:#1d4ed8; border-radius:4px`). The current renderer emits them as plain `<div class="f-tech">` text fields.
3. **Skills inline layout.** `SectionPolicy.skill_variant` exists in the schema (`models.py:149`) and is wired into the customize panel (`CustomizePanel.tsx:626-631`), but the renderer ignores it — both `block` and `inline` produce the same output.

## Investigation

Confirmed in `/tmp/current_*.html` rendered output: link fields use the `::after` pseudo (no arrow in selectable text), tech items render as plain text, skills render with category and tags in the same flex-wrap row regardless of `skill_variant`.

## Decision

1. Inline the arrow in `_render_text_run` so it lives inside the `<a>` tag. Drop the `.f-link::after` CSS rule.
2. Add `chip_keys: list[str] | None = None` to `LayoutHints`. The renderer emits a `<span class="f-chip">` wrapper when `block.key in chip_keys`. Default per-type via `build_section_style`.
3. Branch `_render_section` on `section.type == "skills"` and `section.policy.skill_variant`: `inline` emits a `Category: tag, tag, tag` line; `block` (default) keeps the existing flex layout but uses the chip branch from (2).

## Implementation

- **Step 4 — Inline arrow.** `api/app/services/renderer/html.py`: `_render_text_run` appends `<span aria-hidden="true"> ↗</span>` to the link's inner content; deleted `.f-link::after` CSS rule at the rendered `<style>` block.
- **Step 5a — `chip_keys`.** `api/app/schema/models.py`: added `chip_keys: list[str] | None = None` to `LayoutHints`. `api/app/services/renderer/builders/__init__.py`: `build_section_style` sets the default `LayoutHints` based on section type. `api/app/services/renderer/html.py`: `_render_field_block` accepts `chip_keys` and emits a `<span class="f-chip">` wrapper when matched. `_render_entry` and `_render_field_row` thread the value down. CSS rule `.f-chip { ... }` added to the rendered `<style>` block.
- **Step 5b — Skills inline.** `api/app/services/renderer/html.py`: `_render_section` branches on `section.type == "skills"` and `section.policy.skill_variant`; inline mode builds a single `<div class="f-skills-inline">Category: tag, tag, tag</div>` per entry; block mode keeps the default flex layout but routes tags through the chip branch.
- **Codegen.** `web/src/generated/schema.ts` regenerated via `npm run codegen` after the `models.py` change.
- **Tests.** `api/tests/test_html_renderer.py`: link-arrow assertions updated; chip pill + skills inline branches covered with new tests. `api/tests/test_resolve.py` untouched (skill_variant cascade was already covered).

## Verification

- Pytest: `tests/test_html_renderer.py` and `tests/test_resolve.py` — 43+ passed.
- Rendered HTML:
  - Link arrows: `<span aria-hidden="true"> ↗</span>` present in every link field (3 per generic-modern sample).
  - Chip pills: `<span class="f-chip">Python</span>` for projects tech_stack items.
  - Skills inline: `<div class="f-skills-inline">Category: tag, tag, tag</div>` when `skill_variant=inline`.

## Follow-up

The legacy-era entry `FEAT-01KZ708J2NVNK63N0R4QHX7ZGM` (Skills inline layout variant) is superseded by this entry — the renderer branch this work implements replaces the stale legacy-era plan.
