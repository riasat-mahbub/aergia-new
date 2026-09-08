#!/usr/bin/env node

import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const OPERATIONS = new Set([
  "replace_description",
  "replace_rich_text",
  "rewrite_rich_text",
  "remove_bullet",
  "reorder_bullets",
  "remove_entry",
  "reorder_entries",
  "add_library_entry",
  "create_section",
  "replace_section",
  "remove_section",
  "reorder_sections",
  "report_gap",
]);

const RENDERABLE_SECTION_TYPES = new Set([
  "profile", "experience", "education", "skills", "projects", "languages", "certifications", "research", "extras",
]);

const LIBRARY_KIND_TO_SECTION_TYPE = new Map([
  ["experience", "experience"],
  ["education", "education"],
  ["skill", "skills"],
  ["project", "projects"],
  ["language", "languages"],
  ["certification", "certifications"],
  ["research", "research"],
]);

const PROFILE_IMMUTABLE_FIELDS = [
  "name", "email", "email_link", "phone", "location", "site_text", "site_url", "photo_url", "social_links",
];

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--patch" || argument === "--evidence" || argument === "--output") {
      const value = argv[index + 1];
      if (!value) throw new Error(`${argument} requires a file path`);
      args[argument.slice(2)] = value;
      index += 1;
      continue;
    }
    if (argument === "--help" || argument === "-h") return { help: true };
    throw new Error(`Unknown option: ${argument}`);
  }
  if (!args.patch || !args.evidence) throw new Error("Usage: validate-patch.mjs --evidence evidence.json --patch patch.json [--output tailored-cv.json]");
  return args;
}

async function readJson(path) {
  try {
    return JSON.parse(await readFile(path, "utf8"));
  } catch {
    throw new Error(`Unable to read JSON file: ${path}`);
  }
}

function sectionsFromEvidence(evidence, target = false) {
  const document = target && evidence?.target_cv ? evidence.target_cv : evidence?.cv;
  const sections = Array.isArray(document?.sections)
    ? document.sections
    : Array.isArray(document?.sections?.sections)
      ? document.sections.sections
      : null;
  if (!sections) throw new Error(target ? "Evidence target CV does not contain a sections array" : "Evidence CV does not contain a sections array");
  return sections;
}

function findSection(sections, id) {
  const matches = sections.filter((section) => section?.id === id);
  if (matches.length !== 1) throw new Error(`Expected one section with ID ${id}`);
  return matches[0];
}

function findEntry(section, id) {
  if (!Array.isArray(section?.data)) throw new Error(`Section ${section.id} is not entry-based`);
  const matches = section.data.filter((entry) => entry?.id === id);
  if (matches.length !== 1) throw new Error(`Expected one entry with ID ${id}`);
  return matches[0];
}

function findTarget(section, id) {
  if (section?.type === "profile") {
    if (id !== undefined && id !== null) throw new Error("Profile targets must omit entry_id");
    if (!section.data || typeof section.data !== "object" || Array.isArray(section.data)) {
      throw new Error(`Section ${section.id} has invalid profile data`);
    }
    return section.data;
  }
  return findEntry(section, id);
}

function checkUniqueIds(values, label) {
  if (!Array.isArray(values) || values.length === 0 || values.some((value) => typeof value !== "string" || !value.trim())) {
    throw new Error(`${label} must contain non-empty string IDs`);
  }
  if (new Set(values).size !== values.length) throw new Error(`${label} must contain unique IDs`);
}

function readField(source, fieldPath) {
  if (fieldPath === "*") return source;
  if (typeof fieldPath !== "string" || !fieldPath) return undefined;
  return fieldPath.split(".").reduce((current, part) => (
    current && typeof current === "object" ? current[part] : undefined
  ), source);
}

function isSafeHttpUrl(value) {
  if (typeof value !== "string" || !value.trim() || /[\s\u0000-\u001f\u007f]/.test(value)) return false;
  try {
    const parsed = new URL(value);
    return (parsed.protocol === "http:" || parsed.protocol === "https:")
      && Boolean(parsed.hostname)
      && !parsed.username
      && !parsed.password;
  } catch {
    return false;
  }
}

function isFieldPath(value) {
  return typeof value === "string"
    && /^(?:\*|[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*)$/.test(value)
    && value.length <= 128;
}

function hasValue(value) {
  return value !== undefined && value !== null;
}

function rejectEvidenceFields(reference, fields, label) {
  if (fields.some((field) => hasValue(reference[field]))) throw new Error(`${label} contains fields for another source`);
}

function validateEvidenceRefs(change, evidence, sections) {
  for (const reference of change.evidence ?? []) {
    if (!reference || typeof reference !== "object") throw new Error("Evidence references must be objects");
    if (reference.source === "cv") {
      if (!reference.section_id || !isFieldPath(reference.field_path)) throw new Error("CV evidence requires section_id and field_path");
      rejectEvidenceFields(reference, ["library_entry_id", "source_row_id", "source_hash", "url", "title", "excerpt"], "CV evidence");
      const section = findSection(sections, reference.section_id);
      const source = findTarget(section, reference.entry_id);
      if (readField(source, reference.field_path) === undefined) throw new Error("CV evidence field does not exist");
      continue;
    }
    if (reference.source === "library") {
      if (!isFieldPath(reference.field_path)) throw new Error("Library evidence requires field_path");
      if (!reference.library_entry_id || !reference.source_row_id || !/^[0-9a-f]{64}$/.test(reference.source_hash ?? "")) {
        throw new Error("Library evidence requires entry, row, and source hash");
      }
      rejectEvidenceFields(reference, ["section_id", "entry_id", "url", "title", "excerpt"], "Library evidence");
      const source = (evidence.library ?? []).find((entry) => entry?.id === reference.library_entry_id);
      if (!source) throw new Error(`Unknown Library evidence entry ID: ${reference.library_entry_id}`);
      if (source.content_hash !== reference.source_hash) throw new Error("Library evidence hash does not match the packet");
      const row = source.payload?.find((candidate) => candidate?.id === reference.source_row_id);
      if (!row || readField(row, reference.field_path) === undefined) throw new Error("Library evidence field does not exist");
      continue;
    }
    if (reference.source === "web") {
      if (!isSafeHttpUrl(reference.url)) throw new Error("Web evidence requires a safe HTTP(S) URL");
      if (reference.url.length > 2048) throw new Error("Web evidence URL is too long");
      if (typeof reference.title !== "string" || !reference.title.trim() || reference.title.length > 255) {
        throw new Error("Web evidence requires a bounded title");
      }
      if (typeof reference.excerpt !== "string" || !reference.excerpt.trim() || reference.excerpt.length > 4000) {
        throw new Error("Web evidence requires a bounded excerpt");
      }
      rejectEvidenceFields(
        reference,
        ["field_path", "section_id", "entry_id", "library_entry_id", "source_row_id", "source_hash"],
        "Web evidence",
      );
      continue;
    }
    throw new Error(`Unsupported evidence source: ${reference.source}`);
  }
}

function requireStructuralProof(change) {
  if (typeof change.reason !== "string" || !change.reason.trim()) {
    throw new Error(`${change.operation} requires a non-empty reason`);
  }
  if (!Array.isArray(change.evidence) || change.evidence.length === 0) {
    throw new Error(`${change.operation} requires at least one evidence reference`);
  }
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function validateSectionPayload(section) {
  if (!section || typeof section !== "object") throw new Error("Structural changes require a section object");
  if (typeof section.id !== "string" || !section.id.trim()) throw new Error("Section ID is required");
  if (typeof section.type !== "string" || !RENDERABLE_SECTION_TYPES.has(section.type)) {
    throw new Error(`Section type cannot be rendered: ${section.type}`);
  }
  if (typeof section.title !== "string" || !section.title.trim()) throw new Error("Section title is required");
  if (section.enabled !== undefined && typeof section.enabled !== "boolean") throw new Error("Section enabled must be boolean");
  if (section.style !== undefined && section.style !== null && typeof section.style !== "object") {
    throw new Error("Section style must be an object or null");
  }
  if (section.type === "profile") {
    if (!section.data || typeof section.data !== "object" || Array.isArray(section.data)) {
      throw new Error("Profile sections require object data");
    }
    return;
  }
  if (!Array.isArray(section.data)) throw new Error("Entry-based sections require list data");
  if (section.data.length > 0) checkUniqueIds(section.data.map((entry) => entry?.id), "Section entry IDs");
  if (section.type !== "extras") return;
  for (const entry of section.data) {
    if (!Array.isArray(entry.fields)) throw new Error("Extras entries require a fields list");
    for (const field of entry.fields) {
      if (!field || typeof field.label !== "string" || !field.label.trim() || !("value" in field)) {
        throw new Error("Extras fields require a label and value");
      }
    }
  }
}

function assertProfileIdentityUnchanged(before, after) {
  for (const field of PROFILE_IMMUTABLE_FIELDS) {
    if (stableJson(before.data?.[field]) !== stableJson(after.data?.[field])) {
      throw new Error(`Profile identity field cannot be changed: ${field}`);
    }
  }
}

function validateChange(change, evidence, sections, evidenceSections = sections) {
  if (!change || typeof change !== "object") throw new Error("Each change must be an object");
  if (!OPERATIONS.has(change.operation)) throw new Error(`Unsupported operation: ${change.operation}`);
  if (Array.isArray(evidence.supported_operations) && !evidence.supported_operations.includes(change.operation)) {
    throw new Error(`Operation is not advertised by the server: ${change.operation}`);
  }
  validateEvidenceRefs(change, evidence, evidenceSections);

  if (change.operation === "report_gap") {
    if (change.requirement_id !== undefined && change.requirement_id !== null && (typeof change.requirement_id !== "string" || !change.requirement_id.trim())) {
      throw new Error("Gap requirement_id must be a non-empty string when provided");
    }
    if (typeof change.requirement !== "string" || !change.requirement.trim()) throw new Error("Gap requirement is required");
    if (typeof change.reason !== "string" || !change.reason.trim()) throw new Error("Gap reason is required");
    return;
  }

  if (change.operation === "create_section") {
    requireStructuralProof(change);
    validateSectionPayload(change.section);
    if (change.section.type === "profile") throw new Error("A tailoring patch cannot create another profile section");
    if (sections.some((section) => section?.id === change.section.id)) {
      throw new Error(`Section ID is already in use: ${change.section.id}`);
    }
    return;
  }

  if (change.operation === "replace_section") {
    requireStructuralProof(change);
    const current = findSection(sections, change.section_id);
    validateSectionPayload(change.section);
    if (change.section.id !== change.section_id) throw new Error("Replacement section ID must match section_id");
    if (current.type === "profile" || change.section.type === "profile") {
      if (current.type !== "profile" || change.section.type !== "profile") {
        throw new Error("The profile section cannot be replaced by another section type");
      }
      if ((change.section.enabled ?? true) !== true) throw new Error("The profile section must remain enabled");
      assertProfileIdentityUnchanged(current, change.section);
    }
    return;
  }

  if (change.operation === "remove_section") {
    requireStructuralProof(change);
    const current = findSection(sections, change.section_id);
    if (current.type === "profile") throw new Error("The profile section cannot be removed");
    return;
  }

  if (change.operation === "reorder_sections") {
    requireStructuralProof(change);
    const ids = sections.map((section) => section?.id);
    checkUniqueIds(ids, "Evidence section IDs");
    checkUniqueIds(change.section_ids, "section_ids");
    if (change.section_ids.length !== ids.length || !change.section_ids.every((id) => ids.includes(id))) {
      throw new Error("reorder_sections must contain every current section exactly once");
    }
    return;
  }

  const section = findSection(sections, change.section_id);
  if (change.operation === "replace_description" || change.operation === "replace_rich_text") {
    const entry = findTarget(section, change.entry_id);
    const field = change.operation === "replace_description" ? "description" : change.field;
    if (typeof entry[field] !== "string") throw new Error(`${change.operation} requires a plain-string field`);
    if (typeof change.value !== "string" || !change.value.trim()) throw new Error("Text replacement is required");
    return;
  }

  if (change.operation === "remove_entry" || change.operation === "reorder_entries") {
    if (!Array.isArray(section.data)) throw new Error(`${change.operation} requires an entry-based section`);
    const ids = section.data.map((entry) => entry?.id);
    checkUniqueIds(ids, "Evidence entry IDs");
    if (change.operation === "remove_entry") {
      if (!ids.includes(change.entry_id)) throw new Error(`Unknown entry ID: ${change.entry_id}`);
    } else {
      checkUniqueIds(change.entry_ids, "entry_ids");
      if (new Set(change.entry_ids).size !== ids.length || !change.entry_ids.every((id) => ids.includes(id))) {
        throw new Error("reorder_entries must contain every evidence entry exactly once");
      }
    }
    return;
  }

  if (change.operation === "add_library_entry") {
    const library = Array.isArray(evidence.library) ? evidence.library : [];
    const source = library.find((entry) => entry?.id === change.library_entry_id);
    if (!source) throw new Error(`Unknown Library entry ID: ${change.library_entry_id}`);
    if (!change.source_row_id) throw new Error("Library additions require source_row_id");
    const sourceRow = source.payload?.find((row) => row?.id === change.source_row_id);
    if (!sourceRow) throw new Error(`Unknown Library source row ID: ${change.source_row_id}`);
    if (LIBRARY_KIND_TO_SECTION_TYPE.get(source.kind) !== section.type) {
      throw new Error("Library source kind does not match the target section");
    }
    if (change.entry_id !== undefined && change.entry_id !== null && !String(change.entry_id).trim()) {
      throw new Error("Library addition entry_id must be non-empty when provided");
    }
    if (change.entry_id && section.data?.some((entry) => entry?.id === change.entry_id)) {
      throw new Error(`CV entry ID is already in use: ${change.entry_id}`);
    }
    return;
  }

  const entry = findTarget(section, change.entry_id);
  const blocks = entry?.[change.field];
  if (!Array.isArray(blocks)) throw new Error(`${change.operation} requires canonical rich-text blocks`);
  const block = blocks.find((candidate) => candidate?.id === change.block_id);
  if ((change.operation === "remove_bullet" || change.operation === "reorder_bullets") && !block) {
    throw new Error(`Unknown rich-text block ID: ${change.block_id}`);
  }
  if (change.operation === "rewrite_rich_text") {
    if (!Array.isArray(change.value) || change.value.length === 0) throw new Error("Rich-text replacement is required");
    checkUniqueIds(change.value.map((candidate) => candidate?.id), "Rich-text block IDs");
    for (const candidate of change.value) checkUniqueIds(candidate?.items?.map((item) => item?.id), "Rich-text item IDs");
    return;
  }
  if (!block || block.type !== "bullet_list") throw new Error(`${change.operation} requires a bullet-list block`);
  const itemIds = block.items?.map((item) => item?.id) ?? [];
  checkUniqueIds(itemIds, "Evidence bullet IDs");
  if (change.operation === "remove_bullet" && !itemIds.includes(change.item_id)) throw new Error(`Unknown bullet ID: ${change.item_id}`);
  if (change.operation === "reorder_bullets") {
    checkUniqueIds(change.item_ids, "item_ids");
    if (new Set(change.item_ids).size !== itemIds.length || !change.item_ids.every((id) => itemIds.includes(id))) {
      throw new Error("reorder_bullets must contain every evidence bullet exactly once");
    }
  }
}

function appendLibraryAddition(sections, evidence, change) {
  const section = findSection(sections, change.section_id);
  if (!Array.isArray(section.data)) throw new Error("Library additions require an entry-based section");
  const source = (evidence.library ?? []).find((entry) => entry?.id === change.library_entry_id);
  const sourceRow = source?.payload?.find((row) => row?.id === change.source_row_id);
  if (!sourceRow) throw new Error(`Unknown Library source row ID: ${change.source_row_id}`);
  // The server chooses a random ID when one is omitted. A local-only ID keeps
  // the preview complete; later patch operations still require an explicit ID.
  const previewId = change.entry_id ?? `local-preview-${change.source_row_id}-${section.data.length + 1}`;
  section.data.push({ ...structuredClone(sourceRow), id: previewId });
  if (section.enabled === false) section.enabled = true;
}

function applyStructuralChange(sections, change) {
  if (change.operation === "create_section") {
    sections.push(structuredClone(change.section));
  } else if (change.operation === "replace_section") {
    const index = sections.findIndex((section) => section?.id === change.section_id);
    sections[index] = structuredClone(change.section);
  } else if (change.operation === "remove_section") {
    const index = sections.findIndex((section) => section?.id === change.section_id);
    sections.splice(index, 1);
  } else if (change.operation === "reorder_sections") {
    const byId = new Map(sections.map((section) => [section.id, section]));
    sections.splice(0, sections.length, ...change.section_ids.map((id) => byId.get(id)));
  }
}

function applyValidatedChange(sections, evidence, change) {
  applyStructuralChange(sections, change);
  if (change.operation === "add_library_entry") {
    appendLibraryAddition(sections, evidence, change);
    return;
  }
  if (["create_section", "replace_section", "remove_section", "reorder_sections", "report_gap"].includes(change.operation)) {
    return;
  }

  const section = findSection(sections, change.section_id);
  if (change.operation === "remove_entry") {
    section.data.splice(section.data.findIndex((entry) => entry?.id === change.entry_id), 1);
    return;
  }
  if (change.operation === "reorder_entries") {
    const entries = new Map(section.data.map((entry) => [entry.id, entry]));
    section.data.splice(0, section.data.length, ...change.entry_ids.map((id) => entries.get(id)));
    return;
  }

  const entry = findTarget(section, change.entry_id);
  const field = change.operation === "replace_description" ? "description" : change.field;
  if (["replace_description", "replace_rich_text", "rewrite_rich_text"].includes(change.operation)) {
    entry[field] = structuredClone(change.value);
    return;
  }

  const blocks = entry[field];
  const block = blocks.find((candidate) => candidate?.id === change.block_id);
  if (change.operation === "remove_bullet") {
    block.items.splice(block.items.findIndex((item) => item?.id === change.item_id), 1);
    if (block.items.length === 0) blocks.splice(blocks.indexOf(block), 1);
    return;
  }
  if (change.operation === "reorder_bullets") {
    const items = new Map(block.items.map((item) => [item.id, item]));
    block.items.splice(0, block.items.length, ...change.item_ids.map((id) => items.get(id)));
  }
}

function materializedDocument(evidence, sections) {
  const source = evidence?.target_cv ?? evidence?.cv;
  const document = structuredClone(source);
  if (Array.isArray(document.sections)) {
    document.sections = sections;
  } else {
    document.sections.sections = sections;
  }
  return document;
}

function validateAndMaterialize(patch, evidence) {
  if (patch?.protocol_version !== 1) throw new Error("Patch protocol_version must be 1");
  if (patch.base_revision !== evidence.base_revision || patch.base_hash !== evidence.base_hash) {
    throw new Error("Patch snapshot identity does not match the evidence packet");
  }
  if (!Array.isArray(patch.changes) || patch.changes.length === 0 || patch.changes.length > 50) {
    throw new Error("Patch changes must contain between 1 and 50 operations");
  }
  const sections = sectionsFromEvidence(evidence, true);
  const evidenceSections = sectionsFromEvidence(evidence);
  const workingSections = structuredClone(sections);
  patch.changes.forEach((change) => {
    validateChange(change, evidence, workingSections, evidenceSections);
    applyValidatedChange(workingSections, evidence, change);
  });
  return materializedDocument(evidence, workingSections);
}

export function validatePatch(patch, evidence) {
  validateAndMaterialize(patch, evidence);
  return { valid: true, operation_count: patch.changes.length };
}

export function materializePatch(patch, evidence) {
  return validateAndMaterialize(patch, evidence);
}

function printHelp() {
  console.log("Usage: validate-patch.mjs --evidence evidence.json --patch patch.json [--output tailored-cv.json]");
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
      printHelp();
    } else {
      const patch = await readJson(args.patch);
      const evidence = await readJson(args.evidence);
      const result = validatePatch(patch, evidence);
      if (args.output) {
        await writeFile(args.output, `${JSON.stringify(materializePatch(patch, evidence), null, 2)}\n`, "utf8");
      }
      console.log(JSON.stringify(result));
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : "Patch validation failed");
    process.exitCode = 1;
  }
}
