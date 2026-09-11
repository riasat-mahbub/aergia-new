#!/usr/bin/env node

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
  // Do not merge source values or rewrite claims locally. The server owns
  // identity injection and canonical normalization.
  return JSON.parse(JSON.stringify(candidate));
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
