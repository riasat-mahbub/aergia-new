import { z } from "zod";

// ---------------------------------------------------------------------------
// Design tokens — mirror of the backend's constrained vocabulary
// ---------------------------------------------------------------------------

// A zone's width. ``narrow`` ≈ 30%, ``half`` ≈ 50%, ``full`` ≈ 100%.
const widthTokenSchema = z.union([
  z.literal("narrow"),
  z.literal("half"),
  z.literal("full"),
  z.literal("auto"),
]);

// Spacing and padding presets.
const spacingTokenSchema = z.union([
  z.literal("none"),
  z.literal("tight"),
  z.literal("comfortable"),
  z.literal("loose"),
]);

// Font families exposed to template authors.
const fontTokenSchema = z.union([
  z.literal("sans-serif"),
  z.literal("serif"),
  z.literal("mono"),
  z.literal("display"),
]);

// Text alignment.
const alignmentTokenSchema = z.union([
  z.literal("left"),
  z.literal("right"),
  z.literal("center"),
  z.literal("justify"),
]);

// Compact / comfortable / minimal — the legacy v2 spacing enum.
const layoutSpacingTokenSchema = z.union([
  z.literal("compact"),
  z.literal("comfortable"),
  z.literal("minimal"),
]);

// A color reference is either a hex literal (``#RRGGBB``) or a named
// palette slot (``palette.<name>``). Renderers define their own palettes.
const HEX_LITERAL = /^#[0-9a-fA-F]{6}$/;
const PALETTE_REF = /^palette\.[a-z][a-z0-9_-]*$/;
const colorRefSchema = z
  .string()
  .refine(
    (v) => HEX_LITERAL.test(v) || PALETTE_REF.test(v),
    { message: "Color must be a hex literal (#RRGGBB) or a palette reference (palette.<name>)" },
  );
// URL scheme validator. Bare domains are rejected at the form layer.
const URL_SCHEME_RE = /^[a-zA-Z][a-zA-Z0-9+.\-]*:/;

/** Validates URL fields on section entries.
 * Empty strings pass (these fields are all optional in profile / projects /
 * certifications). When populated, the value MUST start with a URL scheme
 * such as https://, http://, mailto:, or tel:.
 */
export const urlSchema = z
  .string()
  .refine(
    (v) => v === "" || URL_SCHEME_RE.test(v),
    { message: "URL must start with a scheme (https://, mailto:, tel:, etc.)" },
  );

const socialLinkSchema = z.object({
  label: z.string(),
  url: urlSchema,
  icon: z.string(),  // validated by the editor dropdown; backend trusts it
});

export const profileSchema = z.object({
  name: z.string().min(1, "Name is required"),
  title: z.string().min(1, "Title is required"),
  email: z.string().email("Invalid email address"),
  email_link: z.boolean().default(true),
  phone: z.string().min(1, "Phone is required"),
  location: z.string().min(1, "Location is required"),
  site_text: z.string(),
  site_url: urlSchema,
  summary: z.string().min(1, "Summary is required"),
  photo_url: z.string(),
  social_links: z.array(socialLinkSchema).default([]),
});

export const experienceEntrySchema = z.object({
  id: z.string().min(1),
  company: z.string().min(1, "Company is required"),
  position: z.string().min(1, "Position is required"),
  start_date: z.string().min(1, "Start date is required"),
  end_date: z.string().nullable(),
  current: z.boolean(),
  location: z.string().min(1, "Location is required"),
  description: z.string().min(1, "Description is required"),
});

export const educationEntrySchema = z.object({
  id: z.string().min(1),
  institution: z.string().min(1, "Institution is required"),
  degree: z.string().min(1, "Degree is required"),
  start_date: z.string().min(1, "Start date is required"),
  end_date: z.string().nullable(),
  current: z.boolean(),
  gpa: z.string(),
  summary: z.string().default(""),
});

export const skillGroupSchema = z.object({
  id: z.string().min(1),
  category: z.string().min(1, "Category is required"),
  items: z.array(z.string()),
});

export const projectEntrySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1, "Name is required"),
  url: urlSchema,
  link_text: z.string(),
  start_date: z.string().min(1, "Start date is required"),
  end_date: z.string().nullable(),
  description: z.string().min(1, "Description is required"),
  tech_stack: z.array(z.string()),
});
export const languageEntrySchema = z.object({
  id: z.string().min(1),
  language: z.string().min(1, "Language is required"),
  proficiency: z.string().min(1, "Proficiency is required"),
});

export const certificationEntrySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1, "Name is required"),
  issuer: z.string().min(1, "Issuer is required"),
  date: z.string(),
  credential_url: urlSchema,
});

export const researchEntrySchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1, "Title is required"),
  paper_url: urlSchema,
  paper_link_text: z.string(),
  description: z.string().min(1, "Description is required"),
  publication_date: z.string(),
  publication_value: z.string(),
});

// Sub-schemas for the three-axis SectionInstanceStyle. These mirror the
// codegen-derived TypeScript interfaces in `web/src/generated/schema.ts`.
// `.strict()` rejects unknown keys so typos at the panel become loud
// validation errors rather than silently dropped values.
const textStyleSchema = z.object({
  bold: z.boolean().optional(),
  italic: z.boolean().optional(),
  underline: z.boolean().optional(),
  strike: z.boolean().optional(),
  color: z.string().nullable().optional(),
  link: z.string().nullable().optional(),
  font_size: z
    .union([z.literal("xs"), z.literal("small"), z.literal("normal"), z.literal("large"), z.literal("xl")])
    .nullable()
    .optional(),
}).strict();

const layoutHintsSchema = z.object({
  font_family: z.string().nullable().optional(),
  date_style: z
    .object({ key: z.string().optional(), rangeSep: z.string().optional() })
    .strict()
    .nullable()
    .optional(),
  break_before: z.boolean().optional(),
  keep_together: z.boolean().optional(),
  heading_keeps_with_first: z.boolean().optional(),
  orphans: z.number().optional(),
  widows: z.number().optional(),
}).strict();

const subsectionStyleSchema = z.object({
  text_align: z
    .union([z.literal("left"), z.literal("right"), z.literal("center"), z.literal("justify")])
    .nullable()
    .optional(),
  spacing_before: z.string().nullable().optional(),
  spacing_after: z.string().nullable().optional(),
  background_color: z.string().nullable().optional(),
  section_color: z.string().nullable().optional(),
}).strict();

const sectionPolicySchema = z.object({
  show_title: z.boolean().optional(),
  skill_variant: z.union([z.literal("block"), z.literal("inline")]).nullable().optional(),
}).strict();

const sectionInstanceStyleSchema = z
  .object({
    layout: layoutHintsSchema.optional(),
    subsection: subsectionStyleSchema.optional(),
    policy: sectionPolicySchema.optional(),
    text: z.record(z.string(), textStyleSchema).optional(),
  })
  .strict();

export const sectionInstanceSchema = z.object({
  id: z.string().min(1),
  type: z.string().min(1),
  title: z.string().min(1),
  enabled: z.boolean(),
  data: z.unknown(),
  style: sectionInstanceStyleSchema.optional(),
}).strict();

// Canonical Customizations schema. Strips / rejects legacy top-level
// keys (`{colors, fonts, spacing, flags}`) at the wire boundary.
export const customizationsSchema = z
  .object({
    accent_color: colorRefSchema.nullable().optional(),
    body_font: fontTokenSchema.nullable().optional(),
    heading_font: fontTokenSchema.nullable().optional(),
    default_text_align: alignmentTokenSchema.nullable().optional(),
    spacing: layoutSpacingTokenSchema.nullable().optional(),
    flags: z.record(z.string(), z.boolean()).optional(),
    per_section: z.record(z.string(), sectionInstanceStyleSchema).optional(),
  })
  .strict();

export const sectionInstancesSchema = z.array(sectionInstanceSchema);

// Template manifest schema (v2) — used by the TemplateWizard to gate Save.
// Mirrors the backend's `TemplateManifest` shape but is intentionally a
// partial check: the wizard only writes the keys it can edit, and any
// extra fields the backend permits (e.g. `id`, `assets`) are not exposed.
const zoneStyleSchema = z
  .object({
    width: widthTokenSchema.nullable().optional(),
    background: colorRefSchema.nullable().optional(),
    padding: spacingTokenSchema.nullable().optional(),
  })
  .strict();
const zoneSchema = z
  .object({
    id: z.string().min(1),
    label: z.string().nullable().optional(),
    styles: zoneStyleSchema.optional(),
  })
  .strict();
const layoutDefaultsSchema = z
  .object({
    spacing: layoutSpacingTokenSchema.optional(),
  })
  .strict();
const manifestPolicySchema = z
  .object({
    show_title: z.boolean().optional(),
    skill_variant: z
      .union([z.literal("block"), z.literal("inline")])
      .nullable()
      .optional(),
  })
  .strict();
const policyOverridesSchema = z
  .object({
    by_type: z.record(z.string(), manifestPolicySchema).optional(),
  })
  .strict();
// Closed global styles: the manifest exposes a fixed key set.
// ``accent_color`` is a color ref; ``body_font`` and ``heading_font``
// are font tokens. Unknown keys are rejected.
const globalStylesSchema = z
  .object({
    accent_color: colorRefSchema.nullable().optional(),
    body_font: fontTokenSchema.nullable().optional(),
    heading_font: fontTokenSchema.nullable().optional(),
  })
  .strict();
export const templateManifestSchema = z
  .object({
    manifest_version: z.literal(2),
    name: z.string().min(1),
    description: z.string().nullable().optional(),
    zones: z.array(zoneSchema).optional(),
    placement: z.record(z.string(), z.string()).optional(),
    layout_defaults: layoutDefaultsSchema.optional(),
    policy_overrides: policyOverridesSchema.optional(),
    global_styles: globalStylesSchema.optional(),
  })
  .strict();

export type ProfileData = z.infer<typeof profileSchema>;
export type ExperienceEntry = z.infer<typeof experienceEntrySchema>;
export type EducationEntry = z.infer<typeof educationEntrySchema>;
export type SkillGroup = z.infer<typeof skillGroupSchema>;
export type ProjectEntry = z.infer<typeof projectEntrySchema>;
export type LanguageEntry = z.infer<typeof languageEntrySchema>;
export type CertificationEntry = z.infer<typeof certificationEntrySchema>;
export type ResearchEntry = z.infer<typeof researchEntrySchema>;
export type SectionInstance = z.infer<typeof sectionInstanceSchema>;
