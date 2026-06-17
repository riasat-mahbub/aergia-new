# Template Guide (Phase 7+)

This guide documents the new template system introduced in Phase 7. The old `layout_template` HTML pipeline is no longer used; templates are defined by a manifest and rendered by the HTML renderer.

## How templates work

A template is a **manifest** (JSON) that describes:

1. **Zones** — layout regions (e.g., sidebar, main) with their styles.
2. **Placement** — which section types go into which zone.
3. **Layout defaults** — the template's taste (e.g., `spacing: comfortable`).
4. **Policy overrides** — per-section structural rules that override the renderer defaults.
5. **Global styles** — colors, fonts, default alignment.

The renderer reads the manifest and produces HTML. The CSS is applied via variables defined in the renderer's stylesheet. The user customizes the CV through the customize panel; the customizations cascade with the template defaults.

## Manifest schema

A manifest is a JSON object with these top-level keys:

```json
{
  "manifest_version": 2,
  "name": "Modern",
  "description": "Two-column layout with accent color header and light sidebar",
  "zones": [
    {"id": "sidebar", "styles": {"width": "30%", "background-color": "#f8fafc", "padding": "24px"}},
    {"id": "main",    "styles": {"width": "70%", "padding": "24px"}}
  ],
  "placement": {
    "profile": "sidebar",
    "experience": "main",
    "education": "main",
    "skills": "main",
    "projects": "main",
    "languages": "main",
    "certifications": "main",
    "research": "main"
  },
  "layout_defaults": {
    "spacing": "comfortable"
  },
  "policy_overrides": {},
  "global_styles": {
    "accent_color": "#2563eb",
    "body_font": "Inter, system-ui, sans-serif",
    "heading_font": "Inter, system-ui, sans-serif",
    "default_text_align": "left"
  }
}
```

## Fields

### `zones`

A list of layout regions. Each zone has:
- `id` — used by `placement` to map sections.
- `styles` — CSS properties applied to the zone wrapper (e.g., `width`, `background-color`, `padding`).

### `placement`

A map from section type (or instance ID) to zone ID. The renderer uses this to place sections into zones.

### `layout_defaults`

The template's taste. Currently:
- `spacing` — one of `compact`, `comfortable`, `minimal`. The renderer maps this to CSS variables (`--spacing-section`, `--spacing-subsection`).

### `policy_overrides`

Per-section structural rules. Empty by default. Examples:
- `{"skills": {"skill_variant": "inline"}}` — render Skills as inline text instead of chips.

### `global_styles`

Defaults for global styles. The user overrides these in the customize panel:
- `accent_color` — the accent color used for links and highlights.
- `body_font` — the body font family.
- `heading_font` — the heading font family.
- `default_text_align` — default text alignment for sections.

## How the renderer reads the manifest

The renderer applies defaults in this order:

1. **Manifest defaults** — `layout_defaults`, `global_styles`, `policy_overrides`.
2. **User customizations** — the user's choices from the customize panel.
3. **Per-section overrides** — the user's per-section style choices.

The cascade is the user-cfg > template-default > renderer-default chain. The Resolver produces a fully resolved `RenderModel`; the renderer reads the `RenderModel` and emits HTML.

## Design tokens

The renderer never writes CSS values directly. The template declares a name (`comfortable`); the renderer maps the name to a CSS variable; the stylesheet defines the value.

For example:

```css
:root {
  --spacing-section: 24px;
  --spacing-subsection: 16px;
}

[data-spacing="comfortable"] {
  --spacing-section: 24px;
  --spacing-subsection: 16px;
}

[data-spacing="compact"] {
  --spacing-section: 16px;
  --spacing-subsection: 12px;
}

[data-spacing="minimal"] {
  --spacing-section: 8px;
  --spacing-subsection: 8px;
}
```

The renderer emits `<body data-spacing="comfortable">`. The stylesheet applies the values. Three layers, each independent.

## Editor is schematic

The editor visualizes the document structure (sections, fields, brackets). It does not promise to show the exact spacing, page breaks, or font fallbacks the PDF will produce.

Visual cues (e.g., a "page break" marker) indicate structural intent without literal page boundaries. The user adjusts via the schema, not via dragging.

The user goal is "the rendered CV looks like what the user sees in the preview." The preview is HTML. The HTML is the source of truth.

## Renderer capabilities

The renderer (HTML5 + Chromium) declares its own capabilities. The customize panel reads the renderer's capabilities. The export endpoint reads the renderer's capabilities.

Each capability has a `SupportLevel`:
- `FULL` — the renderer reliably satisfies this; the control is shown normally.
- `BEST_EFFORT` — the renderer tries but can't guarantee; the control is shown with a warning icon.
- `NONE` — the renderer can't satisfy this; the control is hidden.

Examples:
- `break_before`: `FULL` — Chromium honors `break-before: page`.
- `keep_with_next`: `BEST_EFFORT` — Chromium does its best but doesn't guarantee.
- `keep_together`: `BEST_EFFORT` — same.

## Authoring a template

To create a new template:

1. Define the zones (e.g., sidebar + main).
2. Define the placement (which section types go where).
3. Set `layout_defaults` (your taste).
4. Optionally, set `policy_overrides` (if your template genuinely needs different behavior).
5. Upload via the template creator.

Most templates need only two lines of customization:

```json
{
  "layout_defaults": {"spacing": "comfortable"},
  "policy_overrides": {}
}
```

If every template overrides everything, you've accidentally made policies part of template design instead of renderer design. Only override what the template genuinely needs.

## Seed templates

Three system templates ship with the application:

- **Modern** — `spacing: comfortable`, two-column layout.
- **Classic** — `spacing: compact`, single-column layout.
- **Minimal** — `spacing: minimal`, single-column layout.

Each is minimal in `layout_defaults` and `policy_overrides`.

## Comparison: old vs new

| Concern | Old pipeline | New pipeline |
|---------|--------------|--------------|
| Template definition | `layout_template` HTML with `{{zone_id}}` placeholders | Manifest JSON |
| Customization | CSS variables only | Schema-driven + design tokens |
| Renderer | String-concatenation function | Typed tree renderer |
| Code generation | None | Pydantic → TS via `datamodel-code-generator` |
| Capability matrix | None | `RendererSupport` per renderer |
| Section styling | Flat `SectionStyle` (10 fields) | Three axes (TextStyle, SubsectionStyle, LayoutHints) |
| PDF export | HTML rendered by Chromium | HTML rendered by Chromium (same renderer) |
| CSS values | Hardcoded | Design tokens via CSS variables |
