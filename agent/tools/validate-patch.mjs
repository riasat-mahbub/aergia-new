#!/usr/bin/env node

import { readFile } from "node:fs/promises";
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
  "report_gap",
]);

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--patch" || argument === "--evidence") {
      const value = argv[index + 1];
      if (!value) throw new Error(`${argument} requires a file path`);
      args[argument.slice(2)] = value;
      index += 1;
      continue;
    }
    if (argument === "--help" || argument === "-h") return { help: true };
    throw new Error(`Unknown option: ${argument}`);
  }
  if (!args.patch || !args.evidence) throw new Error("Usage: validate-patch.mjs --evidence evidence.json --patch patch.json");
  return args;
}

async function readJson(path) {
  try {
    return JSON.parse(await readFile(path, "utf8"));
  } catch {
    throw new Error(`Unable to read JSON file: ${path}`);
  }
}

function sectionsFromEvidence(evidence) {
  const sections = Array.isArray(evidence?.cv?.sections)
    ? evidence.cv.sections
    : Array.isArray(evidence?.cv?.sections?.sections)
      ? evidence.cv.sections.sections
      : null;
  if (!sections) throw new Error("Evidence CV does not contain a sections array");
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

function validateChange(change, evidence, sections) {
  if (!change || typeof change !== "object") throw new Error("Each change must be an object");
  if (!OPERATIONS.has(change.operation)) throw new Error(`Unsupported operation: ${change.operation}`);
  if (Array.isArray(evidence.supported_operations) && !evidence.supported_operations.includes(change.operation)) {
    throw new Error(`Operation is not advertised by the server: ${change.operation}`);
  }

  if (change.operation === "report_gap") {
    if (typeof change.requirement !== "string" || !change.requirement.trim()) throw new Error("Gap requirement is required");
    if (typeof change.reason !== "string" || !change.reason.trim()) throw new Error("Gap reason is required");
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

export function validatePatch(patch, evidence) {
  if (patch?.protocol_version !== 1) throw new Error("Patch protocol_version must be 1");
  if (patch.base_revision !== evidence.base_revision || patch.base_hash !== evidence.base_hash) {
    throw new Error("Patch snapshot identity does not match the evidence packet");
  }
  if (!Array.isArray(patch.changes) || patch.changes.length === 0 || patch.changes.length > 50) {
    throw new Error("Patch changes must contain between 1 and 50 operations");
  }
  const sections = sectionsFromEvidence(evidence);
  patch.changes.forEach((change) => validateChange(change, evidence, sections));
  return { valid: true, operation_count: patch.changes.length };
}

function printHelp() {
  console.log("Usage: validate-patch.mjs --evidence evidence.json --patch patch.json");
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
      printHelp();
    } else {
      const result = validatePatch(await readJson(args.patch), await readJson(args.evidence));
      console.log(JSON.stringify(result));
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : "Patch validation failed");
    process.exitCode = 1;
  }
}
