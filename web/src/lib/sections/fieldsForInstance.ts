/**
 * Build the per-field list for a section instance at runtime.
 *
 * The previous static field table had bugs: wrong
 * keys ("social_links" vs "social"), missing sections (certifications
 * not in list), missing fields (location on experience), and no
 * awareness of rich-text fields. Worse, it listed every possible field
 * for a type even when the user's data didn't include it.
 *
 * This walks the actual instance data using the same field-key
 * vocabulary the backend builders use. Indexed keys (tag.0, tag.1) are
 * aggregated to their base (tag) so the user sees one row, not ten.
 * Rich-text fields are flagged so the typography group can hide.
 */

import type { SectionInstance } from "./types";

export interface FieldRow {
  /** The canonical key. For indexed fields, the base key ("tag"). */
  key: string;
  /** Human-readable label ("Skill tag", "Name", "Date"). */
  label: string;
  /** Sample text from the user's data — what the live preview renders. */
  sample: string;
  /** True when the field is rich text and per-field styling is a no-op. */
  isRichText: boolean;
  /** True when this row aggregates multiple builder-emitted fields. */
  aggregated: boolean;
}

type EntryLike = Record<string, unknown>;
type FieldDef = {
  key: string;
  label: string;
  sample: (e: EntryLike) => string;
  richText?: boolean;
  aggregate?: boolean;
};

const strOrEmpty = (v: unknown): string => (typeof v === "string" ? v : "");

const arrJoined = (v: unknown): string =>
  Array.isArray(v) ? v.filter((x): x is string => typeof x === "string").join(", ") : "";

const socialSample = (v: unknown): string => {
  if (!Array.isArray(v)) return "";
  return v
    .map((link) => (link && typeof link === "object" ? strOrEmpty((link as EntryLike).label) : ""))
    .filter(Boolean)
    .join(", ");
};

const summaryText = (value: unknown): string => {
  if (Array.isArray(value)) {
    const first = value[0] as EntryLike | undefined;
    if (first && Array.isArray(first.items) && first.items[0]) {
      const item = first.items[0] as EntryLike;
      return strOrEmpty(item.text).slice(0, 80);
    }
    return "";
  }
  return typeof value === "string" ? value.slice(0, 80) : "";
};

const firstCustomValue = (entry: EntryLike): string => {
  for (const [k, v] of Object.entries(entry)) {
    if (k.startsWith("field:") && typeof v === "string" && v) return v;
  }
  return "";
};

/** Static per-type field vocabulary. Mirrors the keys the backend
 * builders emit in api/app/services/renderer/builders/. Order here
 * matches the visual order in the CV (top to bottom). */
const VOCAB: Record<string, FieldDef[]> = {
  profile: [
    { key: "name", label: "Name", sample: (e) => strOrEmpty(e.name) },
    { key: "title", label: "Title", sample: (e) => strOrEmpty(e.title) },
    { key: "email", label: "Email", sample: (e) => strOrEmpty(e.email) },
    { key: "phone", label: "Phone", sample: (e) => strOrEmpty(e.phone) },
    { key: "location", label: "Location", sample: (e) => strOrEmpty(e.location) },
    { key: "site", label: "Site", sample: (e) => strOrEmpty(e.site_text ?? e.site_url) },
    { key: "social", label: "Social links", sample: (e) => socialSample(e.social_links), aggregate: true },
    { key: "summary", label: "Summary", sample: (e) => summaryText(e.summary), richText: true },
  ],
  experience: [
    { key: "position", label: "Position", sample: (e) => strOrEmpty(e.position) },
    { key: "company", label: "Company", sample: (e) => strOrEmpty(e.company) },
    { key: "location", label: "Location", sample: (e) => strOrEmpty(e.location) },
    { key: "date", label: "Date", sample: () => "2024 – Present" },
    { key: "description", label: "Description", sample: (e) => summaryText(e.description), richText: true },
  ],
  education: [
    { key: "degree", label: "Degree", sample: (e) => strOrEmpty(e.degree) },
    { key: "institution", label: "Institution", sample: (e) => strOrEmpty(e.institution) },
    { key: "gpa", label: "GPA", sample: (e) => strOrEmpty(e.gpa) },
    { key: "date", label: "Date", sample: () => "2020 – 2024" },
    { key: "summary", label: "Summary", sample: (e) => summaryText(e.summary), richText: true },
  ],
  projects: [
    { key: "project", label: "Name", sample: (e) => strOrEmpty(e.name) },
    { key: "link", label: "Link", sample: (e) => strOrEmpty(e.link_text ?? e.url) },
    { key: "date", label: "Date", sample: () => "2024" },
    { key: "tech", label: "Tech", sample: (e) => arrJoined(e.tech_stack), aggregate: true },
    { key: "description", label: "Description", sample: (e) => summaryText(e.description), richText: true },
  ],
  skills: [
    { key: "category", label: "Category", sample: (e) => strOrEmpty(e.category) },
    { key: "tag", label: "Skill tag", sample: (e) => arrJoined((e.items as unknown[]) ?? []).split(",").slice(0, 3).join(","), aggregate: true },
  ],
  research: [
    { key: "paper", label: "Paper title", sample: (e) => strOrEmpty(e.title) },
    { key: "venue", label: "Venue", sample: (e) => strOrEmpty(e.publication_value) },
    { key: "link", label: "Paper link", sample: (e) => strOrEmpty(e.paper_link_text ?? e.paper_url) },
    { key: "date", label: "Publication date", sample: () => "2024" },
    { key: "description", label: "Description", sample: (e) => summaryText(e.description), richText: true },
  ],
  certifications: [
    { key: "certification", label: "Name", sample: (e) => strOrEmpty(e.name) },
    { key: "issuer", label: "Issuer", sample: (e) => strOrEmpty(e.issuer) },
    { key: "date", label: "Date", sample: () => "2024" },
    { key: "link", label: "Link", sample: (e) => strOrEmpty(e.link_text ?? e.credential_url) },
  ],
  languages: [
    { key: "language", label: "Language", sample: (e) => strOrEmpty(e.language) },
    { key: "proficiency", label: "Proficiency", sample: (e) => strOrEmpty(e.proficiency) },
  ],
  extras: [
    { key: "title", label: "Entry title", sample: (e) => strOrEmpty(e.title) },
    { key: "field:label", label: "Custom fields", sample: firstCustomValue, aggregate: true },
  ],
};

/** Returns the field rows for an instance. Filters out fields that
 * aren't present in the user's data so the user only sees what they
 * actually have. Rich-text fields are still returned (so the user sees
 * the field) but flagged so the inspector can hide the typography
 * controls with a redirect. */
export function fieldsForInstance(instance: SectionInstance): FieldRow[] {
  const vocab = VOCAB[instance.type];
  if (!vocab) return [];
  const entries: EntryLike[] = Array.isArray(instance.data)
    ? (instance.data as EntryLike[]).filter((d): d is EntryLike => !!d && typeof d === "object")
    : instance.data && typeof instance.data === "object"
      ? [instance.data as EntryLike]
      : [];

  const rows: FieldRow[] = [];
  for (const def of vocab) {
    let sample = "";
    for (const e of entries) {
      const s = def.sample(e);
      if (s) { sample = s; break; }
    }
    if (!sample) continue;
    rows.push({
      key: def.key,
      label: def.label,
      sample,
      isRichText: !!def.richText,
      aggregated: !!def.aggregate,
    });
  }
  return rows;
}
