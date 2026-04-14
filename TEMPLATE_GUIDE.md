# User Template Guide

## Overview

User templates let you create custom CV layouts while keeping the same customization controls (colors, fonts, spacing) as the built-in templates. Instead of writing raw HTML with JavaScript data injection, you write a layout template with placeholders — the system renders your CV sections and inserts them into your design.

## How It Works

Both system templates (Modern, Classic, Minimal) and user templates follow the same rendering pipeline:

1. The system generates section panel HTML using built-in renderers
2. Panels are split into **sidebar** (profile/contact) and **main** (all other sections)
3. Panels are inserted into your layout template at placeholder positions
4. CSS custom properties are substituted with the user's customization choices (colors, fonts, spacing)

This means: **your design stays intact, but the CustomizePanel still works.**

## Template Structure

A user template is an HTML file that defines your layout using two placeholders and CSS variables:

### Placeholders

| Placeholder | Purpose |
|---|---|
| `{{sidebar}}` | Where profile/contact sections render (left column in 2-column layouts) |
| `{{main}}` | Where all other sections render (experience, education, skills, etc.) |

Both placeholders are required. The system replaces them with rendered section panels.

### CSS Custom Properties

Your template can use CSS variables that the CustomizePanel controls:

| Variable | Controlled By | Default |
|---|---|---|
| `var(--accent)` | Accent color | `#2563eb` |
| `var(--bg-sidebar)` | Sidebar background | `#f8fafc` |
| `var(--header)` | Header color | `#000000` |
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
2. **Both placeholders**: `{{sidebar}}` and `{{main}}` must appear somewhere in the body
3. **CSS custom properties**: Use `var(--accent)`, `var(--body-font)`, etc. for customizable values
4. **Print styles**: Include `@media print` rules for PDF export

### Example: Two-Column Template

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

    .sidebar {
      width: 30%;
      padding: 24px;
      background-color: var(--bg-sidebar);
      border-right: 3px solid var(--accent);
    }

    .main {
      width: 70%;
      padding: 24px;
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

    /* Print styles */
    @page { size: A4; margin: 0; }
    @media print {
      body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="sidebar">
      {{sidebar}}
    </div>
    <div class="main">
      <div class="accent-bar"></div>
      {{main}}
    </div>
  </div>
</body>
</html>
```

### Example: Single-Column Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{name}} — CV</title>
  <style>
    body {
      font-family: var(--body-font);
      color: var(--text);
      max-width: 210mm;
      margin: 0 auto;
      padding: 32px;
    }

    .section-title {
      font-family: var(--heading-font);
      color: var(--heading);
      font-size: 1rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 8px;
    }

    .divider {
      border-top: 1px solid var(--divider);
      margin: 16px 0;
    }

    @page { size: A4; margin: 0; }
    @media print {
      body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
  </style>
</head>
<body>
  {{sidebar}}
  {{main}}
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

### Upload Format

The upload endpoint accepts:
- `name` — template display name (auto-derived from filename)
- `layout_template` — the HTML content of your file
- `layout_config` — auto-populated with a default 2-column layout (`{columns: 2, widths: [30, 70]}`)

## How Sections Are Rendered

The system uses built-in section renderers (same as system templates). Each section type produces styled HTML:

### Profile Section
Renders name, title, email, phone, location, summary, and optionally a photo URL. Placed in `{{sidebar}}`.

### Experience / Education / Projects
Renders structured entries with titles, dates, descriptions, and optional details (tech stack, GPA, etc.). Goes in `{{main}}`.

### Skills / Languages / Certifications
Renders categorized skills, language proficiency bars, or certification entries. Goes in `{{main}}`.

You **do not** need to write any JavaScript or data-fetching code — the system handles all section rendering. Your job is purely layout and styling.

## Layout Configuration

The `layout_config` controls how sections are split between sidebar and main:

| Field | Type | Description | Default |
|---|---|---|---|
| `columns` | number | Number of columns (1 or 2) | 2 |
| `widths` | number[] | Column widths in percentages | [30, 70] |
| `margins` | object | Page margins: `{top, bottom, left, right}` | `{top: 40, bottom: 40, left: 40, right: 40}` |

For single-column templates (like Classic or Minimal), set `columns: 1` and `widths: [100]`. Note that the profile section still renders in the sidebar slot — if you want it inline, include `{{sidebar}}` at the top of your `{{main}}` area.

## Advanced Layout Patterns

### Profile Inside Main Column

If you prefer a single-column layout where the profile appears inline:

```html
<body>
  <div class="profile-block">
    {{sidebar}}
  </div>
  <div class="content">
    {{main}}
  </div>
</body>
```

Then style `.profile-block` to display as a full-width header.

### Multi-Column Main Area

You can structure `{{main}}` however you like — it's just a container that the system fills with rendered sections:

```html
<div class="grid">
  <div class="col-left">{{main}}</div>
</div>
```

The system inserts all non-profile sections into the first `{{main}}` placeholder it finds. If you need multiple main areas, use only one `{{main}}` — extra occurrences are left as-is (which may produce unexpected results).

### Custom Section Styling Overrides

Per-section style overrides (font, color, weight) set on individual section instances are applied via inline styles by the system's section renderer. Your layout template doesn't need to handle these — they're injected directly into each section panel's HTML.

## Best Practices

1. **Use CSS variables for everything customizable** — this is what makes the CustomizePanel work
2. **Keep `{{sidebar}}` and `{{main}}` as direct children of your layout containers** — avoid wrapping them in complex nested structures that might interfere with rendering
3. **Include print styles** — PDF export uses Playwright headless Chromium; without `@media print` rules, colors may not render correctly
4. **Set `max-width: 210mm` on the body or main container** — this matches A4 width and ensures WYSIWYG preview
5. **Use `box-sizing: border-box` globally** — prevents padding from breaking your layout dimensions
6. **Test with all section types** — make sure your layout handles empty sections gracefully (the system renders a "No data" placeholder for disabled/empty sections)

## Troubleshooting

### Sections not appearing
- Verify both `{{sidebar}}` and `{{main}}` placeholders are present in your HTML
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
| Layout definition | Built-in (Python renderers) | Your HTML with `{{sidebar}}`/`{{main}}` |
| Customization panel | Full control | Works via CSS variables |
| Section rendering | System-generated | Same system renderers |
| Colors/fonts/spacing | Live-editable | Live-editable via CSS vars |
| Per-section overrides | Supported | Supported |
| PDF export | Works | Works (same pipeline) |
