# User Template Guide

## Overview

User templates let you create custom CV layouts while keeping the same customization controls (colors, fonts, spacing) as the built-in templates. Instead of writing raw HTML with JavaScript data injection, you write a layout template with zone placeholders — the system renders your CV sections and inserts them into your design.

## How It Works

Both system templates (Modern, Classic, Minimal) and user templates follow the same rendering pipeline:

1. The system generates section panel HTML using built-in renderers
2. Sections are grouped by their target **zone** based on `layout_config.placement`
3. Each zone's sections are inserted into your layout template at `{{zone_id}}` placeholders
4. CSS custom properties are substituted with the user's customization choices (colors, fonts, spacing)

This means: **your design stays intact, but the CustomizePanel still works.**

## Template Structure

A user template is an HTML file that defines your layout using zone placeholders and CSS variables:

### Zone Placeholders

| Placeholder | Purpose |
|---|---|
| `{{zone_id}}` | Where sections assigned to that zone render (e.g., `{{sidebar}}`, `{{main}}, {{left-col}}`) |

Zone IDs are defined in the template's `layout_config.zones`. The system replaces **all occurrences** of each placeholder with rendered section panels for all sections mapped to that zone.

**Every zone ID defined in your `layout_config` must appear in your HTML body.** If you provide a `layout_config`, any extra `{{zone_id}}` placeholders not matching a defined zone are replaced with empty strings. If you skip zone configuration entirely, the system auto-generates zones from your HTML by scanning for `{{zone}}` placeholders and assigning all sections to the first zone found. Data variables like `{{name}}` in your template are preserved as-is.

> **Note on placeholder syntax:** Placeholders must use the exact format `{{zone_id}}` — no spaces inside, lowercase recommended for zone IDs (e.g., `{{sidebar}}`, not `{{ sidebar }}` or `{{Sidebar}}`). The system replaces all occurrences of each placeholder throughout the entire HTML document.

### CSS Custom Properties

Your template can use CSS variables that the CustomizePanel controls:

| Variable | Controlled By | Default |
|---|---|---|
| `var(--accent)` | Accent color | `#2563eb` |
| `var(--bg-sidebar)` | Sidebar background | `#f8fafc` |
| `var(--divider)` | Divider color | `#d1d5db` |
| `var(--text)` | Body text color | `#374151` |
| `var(--heading)` | Heading color | `#111827` |
| `var(--body-font)` | Body font family | `Inter, system-ui, sans-serif` |
| `var(--heading-font)` | Heading font family | Same as body font |
| `var(--section-gap)` | Spacing between sections | `24px` |

## Template Requirements

### Basic Structure

Your template should be a complete HTML document:

1. **HTML5 boilerplate**: `<!DOCTYPE html>` with proper `<html>`, `<head>`, and `<body>` tags
2. **Zone placeholders**: All zone IDs from your `layout_config.zones` must appear somewhere in the body
3. **CSS custom properties**: Use `var(--accent)`, `var(--body-font)`, etc. for customizable values
4. **Print styles**: Include `@media print` rules for PDF export

### Zone Configuration (Upload Time)

When uploading a template, you can optionally define zones and placement mapping:

**Zones JSON** — defines named zones with their container styles:
```json
[
  { "id": "sidebar", "row": 0, "styles": { "width": "30%", "background-color": "#f8fafc", "padding": "24px" } },
  { "id": "main", "row": 0, "styles": { "padding": "24px" } }
]
```

The optional `row` field controls horizontal layering. Zones with the same `row` value share a horizontal row (their widths sum to 100%). Zones in different rows stack vertically. Zones without a `row` field default to `row: 0`.

**Placement JSON** — maps each section type to a zone ID:
```json
{
  "profile": "sidebar",
  "experience": "main",
  "education": "main",
  "skills": "main",
  "projects": "main",
  "languages": "main",
  "certifications": "main"
}
```

## Examples

### Example: Two-Column Template

**Zone config:**
```json
[
  { "id": "sidebar", "row": 0, "styles": { "width": "30%", "padding": "24px", "background-color": "#f8fafc" } },
  { "id": "main", "row": 0, "styles": { "padding": "24px" } }
]
```

**Placement:**
```json
{
  "profile": "sidebar",
  "experience": "main",
  "education": "main",
  "skills": "main",
  "projects": "main",
  "languages": "main",
  "certifications": "main"
}
```

**HTML:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{name}} — CV</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      font-family: var(--body-font);
      color: var(--text);
      max-width: 210mm;
      margin: 0 auto;
    }

    .container {
      display: flex;
      min-height: 297mm;
    }

    /* Section styling */
    .section-title {
      font-family: var(--heading-font);
      color: var(--heading);
      font-size: 1rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 8px;
    }

    /* Accent bar */
    .accent-bar {
      height: 4px;
      width: 64px;
      background-color: var(--accent);
      margin-bottom: 24px;
    }

    @page { size: A4; margin: 0; }
    @media print {
      body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="sidebar-zone">
      {{sidebar}}
    </div>
    <div class="main-zone">
      <div class="accent-bar"></div>
      {{main}}
    </div>
  </div>
</body>
</html>
```

### Example: Three-Column Layout

**Zone config:**
```json
[
  { "id": "left", "row": 0, "styles": { "width": "20%", "padding": "24px" } },
  { "id": "center", "row": 0, "styles": { "width": "50%", "padding": "24px" } },
  { "id": "right", "row": 0, "styles": { "width": "30%", "padding": "24px" } }
]
```

**Placement:**
```json
{
  "profile": "left",
  "skills": "left",
  "languages": "left",
  "experience": "center",
  "projects": "center",
  "education": "right",
  "certifications": "right"
}
```

**HTML:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{name}} — CV</title>
  <style>
    body { font-family: var(--body-font); color: var(--text); max-width: 210mm; margin: 0 auto; }

    .container { display: flex; min-height: 297mm; }

    @page { size: A4; margin: 0; }
    @media print {
      body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="left-col">{{left}}</div>
    <div class="center-col">{{center}}</div>
    <div class="right-col">{{right}}</div>
  </div>
</body>
</html>
```

## Customization Panel Integration

When a user selects your template, the CustomizePanel still appears in the sidebar (unlike the old system where it was hidden for user templates). The controls work as follows:

### Colors
Changes to accent, sidebar bg, header, divider, text, and heading colors are applied via CSS variable substitution. Your template uses `var(--accent)` etc., and the system replaces them with the user's chosen values at render time.

### Fonts
Body font and heading font selections update `var(--body-font)` and `var(--heading-font)`.

### Spacing
The section gap slider updates `var(--section-gap)`, which you can use in margin/padding declarations like `margin-bottom: var(--section-gap)`.

## Uploading a Template

1. Open the template selector modal (click "Select Template" in the Customize panel)
2. Scroll to **Add New Template** at the bottom
3. Click **Choose file** and select your `.html` file
4. The template name is auto-generated from the filename (e.g., `mit-cv-template.html` → `mit-cv-template`)

### Optional: Configure Zones

Before uploading, click **"Configure zones for new template"** to define your zone structure:

1. **Zones JSON** — defines named zones with their container styles (CSS properties as kebab-case keys/values). Each zone gets a `{{zone_id}}` placeholder in your HTML.
2. **Placement JSON** — maps each section type (`profile`, `experience`, `education`, `skills`, `projects`, `languages`, `certifications`) to a zone ID.

If you skip zone configuration, the system auto-generates zones from your template HTML by scanning for `{{zone}}` placeholders and assigning all sections to the first zone found. This means templates work out of the box without any configuration. Data variables like `{{name}}` in your HTML are preserved as-is.

## How Sections Are Rendered

The system uses built-in section renderers (same as system templates). Each section type produces styled HTML:

### Profile Section
Renders name, title, email, phone, location, summary, and optionally a photo URL. Where it appears depends on placement mapping.

### Experience / Education / Projects
Renders structured entries with titles, dates, descriptions, and optional details (tech stack, GPA, etc.). Where they appear depends on placement mapping.

### Skills / Languages / Certifications
Renders categorized skills, language proficiency bars, or certification entries. Where they appear depends on placement mapping.

You **do not** need to write any JavaScript or data-fetching code — the system handles all section rendering. Your job is purely layout and styling.

## Layout Configuration

The `layout_config` controls how sections are grouped into zones and where they render:

| Field | Type | Description |
|---|---|---|
| `zones` | object[] | Named zones with container styles (`id`, `row`, `styles`) |
| `placement` | object | Maps section types to zone IDs (e.g., `"profile": "sidebar"`) |
| `rowHeights` | object | Optional. Maps row numbers to height percentages (e.g., `{ "0": "60%", "1": "40%" }`). Rows without an entry default to equal distribution. |

### Zone Object Structure

```json
{
  "id": "sidebar",
  "row": 0,
  "label": "Sidebar",
  "styles": {
    "width": "30%",
    "background-color": "#f8fafc",
    "padding": "24px"
  }
}
```

### Placement Object Structure

```json
{
  "profile": "sidebar",
  "experience": "main",
  "education": "main",
  "skills": "main",
  "projects": "main",
  "languages": "main",
  "certifications": "main"
}
```

Every section type (profile, experience, education, skills, projects, languages, certifications) should be mapped to a zone ID. Any unmapped section types default to the `main` zone.

## Advanced Layout Patterns

### Overlapping Zones

You can create overlay effects by positioning zones absolutely:

```json
[
  { "id": "background", "row": 0, "styles": { "position": "absolute", "top": "0", "left": "0", "width": "100%", "height": "120px", "background-color": "#1e3a5f" } },
  { "id": "main", "row": 0, "styles": { "padding": "24px", "margin-top": "80px" } }
]
```

### Multi-Row Layouts

Zones with the same `row` value are rendered as horizontal columns within that row. Zones in different rows stack vertically, each row taking a full-width flex container.

**Zone config:**
```json
[
  { "id": "header", "row": 0, "styles": { "width": "100%", "padding": "16px 32px", "background-color": "#1e3a5f", "color": "#ffffff" } },
  { "id": "sidebar", "row": 1, "styles": { "width": "25%", "padding": "24px", "background-color": "#f8fafc" } },
  { "id": "main", "row": 1, "styles": { "width": "75%", "padding": "24px" } },
  { "id": "footer", "row": 2, "styles": { "width": "100%", "padding": "12px 32px", "background-color": "#f3f4f6", "text-align": "center" } }
]
```

**Placement:**
```json
{
  "profile": "header",
  "experience": "main",
  "education": "main",
  "skills": "sidebar",
  "projects": "main",
  "languages": "sidebar",
  "certifications": "footer"
}
```

**Row heights** (optional) — controls how much vertical space each row takes:
```json
{
  "0": "20%",
  "1": "60%",
  "2": "20%"
}
```

If `rowHeights` is omitted, rows split the available height equally. Heights are percentages that sum to 100%.

This creates a layout with:
- **Row 0**: Full-width header with profile (20% height)
- **Row 1**: Sidebar (25%) + Main (75%) side by side (60% height)
- **Row 2**: Full-width footer with certifications (20% height)

Widths within each row sum to 100%. Row heights across all rows sum to 100%. The Customize panel provides a proportional vertical bar where you can drag handles to resize row heights, drag grip icons to reorder rows, and drag horizontal handles to resize zones within each row.

### Section Grouping Within a Zone

Sections within the same zone are rendered in the order they appear in the CV's section list. You can control this order via the Customize panel's section reordering controls. The spacing between sections is controlled by `var(--section-gap)`.

### Custom Section Styling Overrides

Per-section style overrides (font, color, weight) set on individual section instances are applied via inline styles by the system's section renderer. Your layout template doesn't need to handle these — they're injected directly into each section panel's HTML.

## Best Practices

1. **Use CSS variables for everything customizable** — this is what makes the CustomizePanel work
2. **Every zone ID defined in `layout_config.zones` must appear in your HTML** — each zone needs a corresponding `{{zone_id}}` placeholder. The system replaces all occurrences of each placeholder, so duplicates (e.g., in comments) are harmless but unnecessary.
3. **Include print styles** — PDF export uses Playwright headless Chromium; without `@media print` rules, colors may not render correctly
4. **Set `max-width: 210mm` on the body or main container** — this matches A4 width and ensures WYSIWYG preview
5. **Use `box-sizing: border-box` globally** — prevents padding from breaking your layout dimensions
6. **Test with all section types** — make sure your layout handles empty sections gracefully (the system renders a "No data" placeholder for disabled/empty sections)
7. **Keep zone IDs simple** — use alphanumeric characters, hyphens, and underscores (e.g., `sidebar`, `left-col`, `main-area`)
8. **Avoid zone-like names in data variables** — names like `name`, `company`, or `title` are safe as data variables. But avoid using zone-like words such as `sidebar`, `footer`, `nav`, or `main` as variable names, since they will be treated as zones and replaced with empty content if no instances exist for them.
9. **Use multi-row layouts for complex CVs** — if you need a header/footer alongside a sidebar+main body, use different `row` values. Zones in the same row share 100% width horizontally; different rows stack vertically.

## Troubleshooting

### Literal zone placeholders showing in preview (e.g., `{{sidebar}}` visible as text)
This usually means the zone placeholder was not replaced during rendering. Check:
- Ensure your template actually contains the zone placeholder (e.g., `{{sidebar}}`, not `{{ sidebar }}` with spaces — spaces are not allowed inside placeholders)
- If you skipped zone configuration, verify the template contains at least one `{{zone}}` placeholder. The system auto-generates zones from your HTML.
- Make sure the placeholder text matches exactly — no extra spaces, different casing, or special characters: `{{sidebar}}` is correct; `{{Sidebar}}`, `{{ sidebar }}`, or `{sidebar}` will not work.

### Sections not appearing
- Verify all zone IDs from your `layout_config.zones` have corresponding `{{zone_id}}` placeholders in your HTML
- Check that every section type in your placement mapping points to a valid zone ID
- If you skipped zone configuration, note that all sections are assigned to the first zone found in your HTML
- Check that the HTML is valid (no unclosed tags, proper nesting)

### Customization controls not affecting appearance
- Ensure you're using `var(--variable-name)` syntax in your CSS (e.g., `color: var(--accent)`)
- Variable names must match exactly: `--accent`, `--bg-sidebar`, `--body-font`, etc.
- Check the browser console for CSS parsing errors

### PDF looks different from preview
- Verify you have `@media print` or `@page` rules with `print-color-adjust: exact`
- Ensure your CSS uses inline-compatible values (some complex CSS features don't translate to PDF)

### Layout breaks with many sections
- Use `overflow` and `min-height` properties on containers
- Consider adding page break controls: `.section { page-break-inside: avoid; }`

## Security Notes

- User templates run server-side during preview and PDF generation (no browser execution)
- Templates are sandboxed — no external network requests, no access to system resources
- Only the section data rendered by the system is inserted into your template
- CSS custom property substitution is safe — only known variable names are replaced

## Comparison: System vs User Templates

| Feature | System Templates | User Templates |
|---|---|---|
| Layout definition | Built-in (Python renderers) | Your HTML with `{{zone_id}}` placeholders |
| Zone configuration | Internal to template | Defined at upload time via JSON |
| Customization panel | Full control | Works via CSS variables |
| Section rendering | System-generated | Same system renderers |
| Colors/fonts/spacing | Live-editable | Live-editable via CSS vars |
| Per-section overrides | Supported | Supported |
| PDF export | Works | Works (same pipeline) |
