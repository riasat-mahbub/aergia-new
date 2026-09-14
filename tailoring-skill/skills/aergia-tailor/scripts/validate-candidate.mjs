#!/usr/bin/env node

import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

export function validateCandidate(candidate, context) {
  assert(candidate && typeof candidate === "object" && !Array.isArray(candidate), "Candidate must be an object");
  assert(typeof candidate.title === "string" && candidate.title.trim(), "Candidate title is required");
  assert(typeof candidate.template_id === "string" && candidate.template_id.trim(), "Candidate template_id is required");
  const templates = Array.isArray(context?.templates) ? context.templates : [];
  assert(templates.some((template) => template?.id === candidate.template_id), "Candidate template is not in the context");
  assert(Array.isArray(candidate.sections) && candidate.sections.length > 0, "Candidate sections are required");
  const ids = new Set();
  let profiles = 0;
  for (const section of candidate.sections) {
    assert(section && typeof section === "object" && !Array.isArray(section), "Every section must be an object");
    assert(typeof section.id === "string" && section.id.trim(), "Every section needs an id");
    assert(!ids.has(section.id), "Section ids must be unique");
    ids.add(section.id);
    if (section.type === "profile") {
      profiles += 1;
      assert(section.enabled !== false, "The profile section must be enabled");
    }
  }
  assert(profiles === 1, "Candidate must contain exactly one profile section");
  assert(candidate.customizations && typeof candidate.customizations === "object" && !Array.isArray(candidate.customizations), "Candidate customizations must be an object");
  return { valid: true, section_count: candidate.sections.length };
}

export function materializeCandidate(candidate) {
  // Do not merge source values or rewrite claims locally. Stable structural
  // rich-text IDs make preview and submit normalization identical.
  const normalized = JSON.parse(JSON.stringify(candidate));
  const fieldsBySection = {
    profile: ["summary"],
    experience: ["description"],
    education: ["summary"],
    projects: ["description"],
    research: ["description"],
  };

  function validId(value) {
    return typeof value === "string" && Boolean(value.trim()) && value.length <= 128;
  }

  function stableId(prefix, path, used) {
    for (let salt = 0; ; salt += 1) {
      const digest = createHash("sha256").update(prefix + "\u0000" + path + "\u0000" + salt).digest("hex").slice(0, 32);
      const id = prefix + "_" + digest;
      if (!used.has(id)) return id;
    }
  }

  for (const section of normalized.sections) {
    const fields = fieldsBySection[section?.type] ?? [];
    const rows = Array.isArray(section?.data)
      ? section.data.map((row, index) => [index, row]).filter(([, row]) => row && typeof row === "object" && !Array.isArray(row))
      : section?.data && typeof section.data === "object"
        ? [[0, section.data]]
        : [];
    for (const [rowIndex, row] of rows) {
      for (const field of fields) {
        const blocks = row[field];
        if (!Array.isArray(blocks)) continue;
        const blockIds = new Set();
        blocks.forEach((block, blockIndex) => {
          if (!block || typeof block !== "object" || Array.isArray(block)) return;
          if (!validId(block.id) || blockIds.has(block.id)) {
            block.id = stableId("rtb", [section.id, rowIndex, field, blockIndex].join("/"), blockIds);
          }
          blockIds.add(block.id);
          if (!Array.isArray(block.items)) return;
          const itemIds = new Set();
          block.items.forEach((item, itemIndex) => {
            if (!item || typeof item !== "object" || Array.isArray(item)) return;
            if (!validId(item.id) || itemIds.has(item.id)) {
              item.id = stableId("rti", [section.id, rowIndex, field, blockIndex, itemIndex].join("/"), itemIds);
            }
            itemIds.add(item.id);
          });
        });
      }
    }
  }
  return normalized;
}

async function readJson(path) {
  try {
    return JSON.parse(await readFile(path, "utf8"));
  } catch {
    throw new Error(`Unable to read JSON file: ${path}`);
  }
}

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (["--context", "--candidate", "--output"].includes(argument)) {
      const value = argv[index + 1];
      if (!value) throw new Error(`${argument} requires a value`);
      args[argument.slice(2)] = value;
      index += 1;
    } else if (argument === "--help" || argument === "-h") {
      return { help: true };
    } else {
      throw new Error(`Unknown option: ${argument}`);
    }
  }
  if (!args.context || !args.candidate) throw new Error("Usage: validate-candidate.mjs --context context.json --candidate candidate.json [--output candidate.json]");
  return args;
}

function printHelp() {
  console.log("Usage: validate-candidate.mjs --context context.json --candidate candidate.json [--output candidate.json]");
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
      printHelp();
    } else {
      const context = await readJson(args.context);
      const candidate = await readJson(args.candidate);
      const result = validateCandidate(candidate, context);
      if (args.output) await writeFile(args.output, `${JSON.stringify(materializeCandidate(candidate), null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
      console.log(JSON.stringify(result));
    }
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : "Candidate validation failed"}\n`);
    process.exitCode = 1;
  }
}
