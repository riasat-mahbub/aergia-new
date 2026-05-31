import type { LayoutConfig } from "./types";

export function layoutConfigToHTML(config: LayoutConfig): string {
  // Zone-only layout: a single implicit row holding every zone in a flex container.
  const zones = config.zones;

  let rowContent = "";
  for (const zone of zones) {
    rowContent += `    {{${zone.id}}}\n`;
  }

  const bodyContent = `  <div style="display:flex;flex:0 0 auto;">\n${rowContent}  </div>\n`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      margin: 0;
      padding: 0;
      font-family: {{body_font}};
      color: var(--text, #374151);
    }
    h1, h2, h3, h4, h5, h6 {
      font-family: {{heading_font}};
      color: var(--heading, #111827);
    }
    {{print_styles}}
  </style>
</head>
<body>
<div style="min-height:297mm;display:flex;flex-direction:column;">
${bodyContent}</div>
</body>
</html>`;
}
