import type { SectionInstance, LayoutConfig } from "./types";

const SECTION_LABELS: Record<string, string> = {
  profile: "Profile",
  experience: "Experience",
  education: "Education",
  skills: "Skills",
  projects: "Projects",
  languages: "Languages",
  certifications: "Certifications",
};

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderProfile(data: Record<string, unknown>): string {
  const parts: string[] = [];
  if (data.photo_url) {
    parts.push(
      `<img src="${escapeHtml(String(data.photo_url))}" alt="" style="width:80px;height:80px;border-radius:9999px;object-fit:cover;margin-bottom:12px;" />`
    );
  }
  parts.push(`<h2 style="font-size:1.25rem;font-weight:700;">${escapeHtml(String(data.name || "Your Name"))}</h2>`);
  parts.push(`<p style="font-size:0.875rem;color:#6b7280;">${escapeHtml(String(data.title || ""))}</p>`);
  const contact: string[] = [];
  if (data.email) contact.push(`<p>${escapeHtml(String(data.email))}</p>`);
  if (data.phone) contact.push(`<p>${escapeHtml(String(data.phone))}</p>`);
  if (data.location) contact.push(`<p>${escapeHtml(String(data.location))}</p>`);
  if (contact.length > 0) {
    parts.push(`<div style="margin-top:8px;font-size:0.75rem;color:#9ca3af;">${contact.join("")}</div>`);
  }
  if (data.summary) {
    parts.push(`<p style="margin-top:12px;font-size:0.875rem;color:#374151;">${escapeHtml(String(data.summary))}</p>`);
  }
  return parts.join("");
}

function renderExperience(data: unknown[] | undefined): string {
  if (!data || data.length === 0) return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>';
  const entries = data as Record<string, unknown>[];
  const items = entries.map((entry) => {
    const end = entry.current ? "Present" : (String(entry.end_date || "") || "");
    const loc = entry.location ? `, ${escapeHtml(String(entry.location))}` : "";
    return `<div style="margin-bottom:16px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <h3 style="font-weight:600;">${escapeHtml(String(entry.position || ""))}</h3>
      <p style="font-size:0.875rem;color:#6b7280;">${escapeHtml(String(entry.company || ""))}${loc}</p>
    </div>
    <p style="font-size:0.75rem;color:#9ca3af;">${escapeHtml(String(entry.start_date || ""))} &ndash; ${escapeHtml(end)}</p>
  </div>
  ${entry.description ? `<p style="margin-top:4px;font-size:0.875rem;color:#374151;">${escapeHtml(String(entry.description))}</p>` : ""}
</div>`;
  });
  return '<div style="display:flex;flex-direction:column;gap:16px;">' + items.join("") + "</div>";
}

function renderEducation(data: unknown[] | undefined): string {
  if (!data || data.length === 0) return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>';
  const entries = data as Record<string, unknown>[];
  const items = entries.map((entry) => {
    const end = entry.current ? "Present" : (String(entry.end_date || "") || "");
    const gpa = entry.gpa ? ` | GPA: ${escapeHtml(String(entry.gpa))}` : "";
    return `<div>
  <h3 style="font-weight:600;">${escapeHtml(String(entry.degree || ""))}</h3>
  <p style="font-size:0.875rem;color:#6b7280;">${escapeHtml(String(entry.institution || ""))}</p>
  <p style="font-size:0.75rem;color:#9ca3af;">${escapeHtml(String(entry.start_date || ""))} &ndash; ${escapeHtml(end)}${gpa}</p>
</div>`;
  });
  return '<div style="display:flex;flex-direction:column;gap:12px;">' + items.join("") + "</div>";
}

function renderSkills(data: unknown[] | undefined): string {
  if (!data || data.length === 0) return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>';
  const groups = data as Record<string, unknown>[];
  const items = groups.map((group) => {
    const skillItems = (group.items as string[] || []).map(
      (item) => `<span style="display:inline-block;background:#f3f4f6;padding:2px 8px;border-radius:4px;font-size:0.75rem;color:#374151;">${escapeHtml(item)}</span>`
    ).join("");
    return `<div>
  <h3 style="font-size:0.875rem;font-weight:600;">${escapeHtml(String(group.category || ""))}</h3>
  <div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">${skillItems}</div>
</div>`;
  });
  return '<div style="display:flex;flex-direction:column;gap:12px;">' + items.join("") + "</div>";
}

function renderProjects(data: unknown[] | undefined): string {
  if (!data || data.length === 0) return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>';
  const entries = data as Record<string, unknown>[];
  const items = entries.map((entry) => {
    let techItems = "";
    if (entry.tech_stack && (entry.tech_stack as string[]).length > 0) {
      techItems = '<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">' +
        (entry.tech_stack as string[]).map(
          (t) => `<span style="display:inline-block;background:#eff6ff;padding:2px 6px;border-radius:4px;font-size:0.75rem;color:#1d4ed8;">${escapeHtml(t)}</span>`
        ).join("") + "</div>";
    }
    const urlLink = entry.url ? `<a href="${escapeHtml(String(entry.url))}" style="font-size:0.75rem;color:#2563eb;">${escapeHtml(String(entry.url))}</a>` : "";
    return `<div>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <h3 style="font-weight:600;">${escapeHtml(String(entry.name || ""))}</h3>
      ${urlLink}
    </div>
    <p style="font-size:0.75rem;color:#9ca3af;">${escapeHtml(String(entry.start_date || ""))} &ndash; ${escapeHtml(String(entry.end_date || "Present") || "Present")}</p>
  </div>
  ${entry.description ? `<p style="margin-top:4px;font-size:0.875rem;color:#374151;">${escapeHtml(String(entry.description))}</p>` : ""}
  ${techItems}
</div>`;
  });
  return '<div style="display:flex;flex-direction:column;gap:12px;">' + items.join("") + "</div>";
}

function renderLanguages(data: unknown[] | undefined): string {
  if (!data || data.length === 0) return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>';
  const items = (data as Record<string, unknown>[]).map((e) =>
    `<div style="display:flex;justify-content:space-between;align-items:center;font-size:0.875rem;"><span>${escapeHtml(String(e.language || ""))}</span><span style="font-size:0.75rem;color:#9ca3af;">${escapeHtml(String(e.proficiency || ""))}</span></div>`
  ).join("");
  return `<div style="display:flex;flex-direction:column;gap:4px;">${items}</div>`;
}

function renderCertifications(data: unknown[] | undefined): string {
  if (!data || data.length === 0) return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>';
  const items = (data as Record<string, unknown>[]).map((entry) => {
    let issuerDate = String(entry.issuer || "");
    if (entry.date) issuerDate += ` \u00b7 ${escapeHtml(String(entry.date))}`;
    const credLink = entry.credential_url
      ? `<a href="${escapeHtml(String(entry.credential_url))}" style="font-size:0.75rem;color:#2563eb;">Credential</a>`
      : "";
    return `<div>
  <h3 style="font-size:0.875rem;font-weight:600;">${escapeHtml(String(entry.name || ""))}</h3>
  <p style="font-size:0.75rem;color:#6b7280;">${escapeHtml(issuerDate)}</p>
  ${credLink}
</div>`;
  });
  return '<div style="display:flex;flex-direction:column;gap:8px;">' + items.join("") + "</div>";
}

const SECTION_RENDERERS: Record<string, (data: unknown) => string> = {
  profile: renderProfile as (data: unknown) => string,
  experience: renderExperience as (data: unknown) => string,
  education: renderEducation as (data: unknown) => string,
  skills: renderSkills as (data: unknown) => string,
  projects: renderProjects as (data: unknown) => string,
  languages: renderLanguages as (data: unknown) => string,
  certifications: renderCertifications as (data: unknown) => string,
};

export function renderSectionHTML(sectionType: string, data: unknown): string {
  const renderer = SECTION_RENDERERS[sectionType];
  if (!renderer) return "";
  return renderer(data);
}

export function renderInstancePanel(instance: SectionInstance): string {
  if (!instance.enabled) return "";
  const sectionType = instance.type;
  const label = instance.title || SECTION_LABELS[sectionType] || sectionType;
  const content = renderSectionHTML(sectionType, instance.data);
  const displayContent = content || '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>';

  const perStyle = (instance.style as Record<string, string> | undefined) || {};
  let wrapperExtra = "";
  let headingExtra = "";
  if (perStyle.font) wrapperExtra += `font-family:${perStyle.font};`;
  if (perStyle.color) {
    wrapperExtra += `color:${perStyle.color};`;
    headingExtra += `color:${perStyle.color};`;
  }
  if (perStyle.weight) headingExtra += `font-weight:${perStyle.weight};`;

  const baseWrapper = "margin-bottom:24px";
  const wrapperStyle = wrapperExtra ? `${baseWrapper};${wrapperExtra}` : baseWrapper;
  const baseHeading = "margin-bottom:8px;font-size:1rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:#1f2937";
  const headingStyle = headingExtra ? `${baseHeading};${headingExtra}` : baseHeading;

  return `<div style="${wrapperStyle}">
<h2 style="${headingStyle}">${escapeHtml(label)}</h2>
${displayContent}
</div>`;
}

function extractZonePlaceholders(template: string): Set<string> {
  const matches = template.match(/\{\{([a-zA-Z0-9_-]+)\}\}/g);
  if (!matches) return new Set();
  return new Set(matches.map((m) => m.slice(2, -2)));
}

function getHeaderInstances(instances: SectionInstance[], layoutConfig: LayoutConfig | undefined): SectionInstance[] {
  if (!layoutConfig?.header?.enabled || !layoutConfig.header.sections.length) return [];
  const headerSet = new Set(layoutConfig.header.sections);
  return instances.filter((i) => i.enabled && headerSet.has(i.type));
}

function groupInstancesByZone(instances: SectionInstance[], layoutConfig: LayoutConfig | undefined, templateContent?: string): Record<string, SectionInstance[]> {
  const headerTypes = new Set(layoutConfig?.header?.enabled ? layoutConfig.header.sections : []);

  if (!layoutConfig || !layoutConfig.placement) {
    // Smart default: scan template for known zone placeholders
    if (templateContent) {
      const zonePlaceholders = extractZonePlaceholders(templateContent);
      if (zonePlaceholders.has("header")) {
        // Profile → header, everything else → main
        const groups: Record<string, SectionInstance[]> = {};
        for (const instance of instances) {
          if (!instance.enabled) continue;
          const sectionType = instance.type;
          const zoneId = sectionType === "profile" ? "header" : "main";
          if (!(zoneId in groups)) {
            groups[zoneId] = [];
          }
          groups[zoneId].push(instance);
        }
        return groups;
      }
    }
    // Fallback: everything goes to "main"
    return { main: instances.filter((i) => i.enabled && !headerTypes.has(i.type)) };
  }

  const groups: Record<string, SectionInstance[]> = {};
  for (const instance of instances) {
    if (!instance.enabled) continue;
    if (headerTypes.has(instance.type)) continue;
    const sectionType = instance.type;
    const zoneId = layoutConfig.placement[sectionType] || "main";
    if (!(zoneId in groups)) {
      groups[zoneId] = [];
    }
    groups[zoneId].push(instance);
  }
  return groups;
}

function buildZoneStyles(zone: { styles?: Record<string, string> }): string {
  const styles = zone.styles || {};
  if (!styles) return "";
  return Object.entries(styles).map(([k, v]) => `${k}:${v};`).join("");
}

export function renderUserTemplateHTML(
  instances: SectionInstance[],
  customizations: Record<string, unknown>,
  layoutTemplate: string,
  defaultCustomizations?: Record<string, unknown>,
  layoutConfig?: LayoutConfig,
): string {
  const merged = mergeCustomizations(defaultCustomizations || {}, customizations);

  // Handle header zone only when explicitly configured
  const headerInstances = getHeaderInstances(instances, layoutConfig);
  let html = layoutTemplate;

  if (layoutConfig?.header?.enabled && html.includes("{{header}}")) {
    if (headerInstances.length > 0) {
      const headerStyles = layoutConfig.header.styles ? buildZoneStyles({ styles: layoutConfig.header.styles }) : "";
      const panels = headerInstances
        .map((i) => `<div style="margin-bottom:var(--section-gap, 24px);">${renderInstancePanel(i)}</div>`)
        .join("");
      html = html.replace(/\{\{header\}\}/g, `<div style="${headerStyles}">${panels}</div>`);
    } else {
      html = html.replace(/\{\{header\}\}/g, "");
    }
  }

  // Group instances by zone (pass template for smart zone detection)
  const groups = groupInstancesByZone(instances, layoutConfig, layoutTemplate);

  // Fill each zone with its sections
  for (const [zoneId, zoneInstances] of Object.entries(groups)) {
    let panels: string;
    if (layoutConfig) {
      const zone = layoutConfig.zones?.find((z) => z.id === zoneId);
      if (zone) {
        const zoneStyles = buildZoneStyles(zone);
        panels = zoneInstances
          .map((i) => `<div style="margin-bottom:var(--section-gap, 24px);">${renderInstancePanel(i)}</div>`)
          .join("");
        html = html.replace(new RegExp(`\\{\\{${zoneId}\\}\\}`, "g"), `<div style="${zoneStyles}">${panels}</div>`);
      } else {
        panels = zoneInstances
          .map((i) => `<div style="margin-bottom:var(--section-gap, 24px);">${renderInstancePanel(i)}</div>`)
          .join("");
        html = html.replace(new RegExp(`\\{\\{${zoneId}\\}\\}`, "g"), panels);
      }
    } else {
      panels = zoneInstances
        .map((i) => `<div style="margin-bottom:var(--section-gap, 24px);">${renderInstancePanel(i)}</div>`)
        .join("");
      html = html.replace(new RegExp(`\\{\\{${zoneId}\\}\\}`, "g"), panels);
    }
  }

  // Replace unknown zone placeholders with empty strings, but preserve data variables (e.g., {{name}})
  const populatedZoneIds = new Set(Object.keys(groups));
  const definedZoneIds = new Set(layoutConfig?.zones?.map((z) => z.id) || []);

  html = html.replace(/\{\{([a-zA-Z0-9_-]+)\}\}/g, (_, id) => {
    // Keep it if it was populated with content
    if (populatedZoneIds.has(id)) return `{{${id}}}`;
    // Keep it if it's defined in layout_config zones (even if empty)
    if (definedZoneIds.has(id)) return `{{${id}}}`;
    // Zone-like names get replaced with empty string
    const zoneNamePatterns = new Set(["main", "sidebar", "header", "left", "right", "center",
      "col", "panel", "zone", "area", "top", "bottom", "nav", "footer", "foot", "aside",
      "primary", "secondary"]);
    if (zoneNamePatterns.has(id) || id.endsWith("-col") || id.endsWith("-zone") || id.endsWith("-panel")) {
      return "";
    }
    // Otherwise leave it — likely a data variable like {{name}}, {{company}}, etc.
    return `{{${id}}}`;
  });

  html = substituteCSSVars(html, merged);

  const printStyles = `
  @page { size: A4; margin: 0; }
  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    img { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
`;

  const fonts = (merged.fonts as Record<string, string>) || {};
  const bodyFont = fonts.body || "system-ui, sans-serif";
  const headingFont = fonts.heading || bodyFont;

  html = html.replace("{{print_styles}}", printStyles);
  html = html.replace("{{body_font}}", bodyFont);
  html = html.replace("{{heading_font}}", headingFont);

  if (!html.includes("<style>")) {
    html = html.replace("<head>", `<head><style>${printStyles}</style>`);
  }

  return html;
}

function mergeCustomizations(defaults: Record<string, unknown>, overrides: Record<string, unknown>): Record<string, unknown> {
  const merged: Record<string, unknown> = {};
  for (const key of Object.keys(defaults)) {
    if (key in overrides) {
      if (typeof defaults[key] === "object" && typeof overrides[key] === "object" && defaults[key] !== null && overrides[key] !== null && !Array.isArray(defaults[key]) && !Array.isArray(overrides[key])) {
        merged[key] = { ...(defaults[key] as Record<string, unknown>), ...(overrides[key] as Record<string, unknown>) };
      } else {
        merged[key] = overrides[key];
      }
    } else {
      merged[key] = defaults[key];
    }
  }
  for (const key of Object.keys(overrides)) {
    if (!(key in merged)) {
      merged[key] = overrides[key];
    }
  }
  return merged;
}

function substituteCSSVars(html: string, customizations: Record<string, unknown>): string {
  const colors = (customizations.colors as Record<string, string>) || {};
  const fonts = (customizations.fonts as Record<string, string>) || {};
  const spacing = (customizations.spacing as Record<string, string>) || {};

  const replacements: Record<string, string | undefined> = {
    "var(--accent)": colors.accent,
    "var(--bg-sidebar)": colors.bg_sidebar,
    "var(--header)": colors.header,
    "var(--divider)": colors.divider,
    "var(--text)": colors.text,
    "var(--heading)": colors.heading,
    "var(--body-font)": fonts.body,
    "var(--heading-font)": fonts.heading,
    "var(--section-gap)": spacing.section_gap,
  };

  let result = html;
  for (const [placeholder, value] of Object.entries(replacements)) {
    if (value !== undefined) {
      result = result.split(placeholder).join(value);
    }
  }
  return result;
}
