---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KZWDAM3ABZTF40H4PD7N77SZ
TYPE: feature
STATUS: DONE
PRIORITY: Low
SEVERITY: null
EFFORT: S
OWNER: riasat
CONFIDENCE: High
TAGS:
- renderer
- customize
- heading
RELATIONS: null
AFFECTS:
  files:
    - api/app/schema/models.py
    - api/app/services/renderer/html.py
    - web/src/components/customization/CustomizePanel.tsx
    - web/src/generated/schema.ts
    - api/tests/test_html_renderer.py
LINKS:
  plan: local://legacy-look-preservation-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-13T03:00:00+00:00'
UPDATED_AT: '2026-08-13T03:00:00+00:00'
---

# Per-section heading divider

## Background

The legacy `default_customizations.flags.underline_section_titles` flag added a horizontal rule beneath each section heading. The current pipeline has no equivalent — `SectionPolicy` only carries `show_title` and `skill_variant`. The user wanted the divider back as a per-section opt-in.

## Investigation

Looked at the legacy flag handling in `ir.py` and the `--divider` CSS variable emitted in the legacy renderer's `<style>` block. Confirmed the visual: `border-bottom:1px solid var(--heading, #1f2937); padding-bottom:4px;` on the `<h2>`. The current `--accent` CSS var carries the section accent color, so using `var(--accent, #1f2937)` matches the modern theme.

## Decision

Add `SectionPolicy.heading_divider: bool = False`. Renderer branches in `_render_heading` to append the border + padding declarations. Customize panel exposes a checkbox next to `show_title` under the existing "Section policy" disclosure.

## Implementation

- `api/app/schema/models.py`: added `heading_divider: bool = False` to `SectionPolicy` after `show_title`.
- `api/app/services/renderer/html.py`: `_render_heading` appends `border-bottom:1px solid var(--accent,#1f2937)` and `padding-bottom:4px` to the `<h2>` inline style when `policy.heading_divider` is True.
- `web/src/components/customization/CustomizePanel.tsx`: added a "Heading divider (underline)" checkbox next to the existing Show title control, under "Section policy".
- `web/src/generated/schema.ts`: regenerated; `SectionPolicy.heading_divider` now appears.
- `api/tests/test_html_renderer.py`: `test_heading_divider_emits_border_bottom_and_padding` covers the new renderer branch.

## Verification

- Pytest: `tests/test_html_renderer.py` and `tests/test_resolve.py` — 46 passed.
- Frontend tests: `npx vitest run` — 225 passed.
- TypeScript: `npx tsc -b` clean.
- Customize panel: heading_divider checkbox visible under Section policy; flips the policy field on the wire.

## Follow-up

None. Step 5d of `local://legacy-look-preservation-plan.md` is closed.
