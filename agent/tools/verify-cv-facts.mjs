#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const NUMBER_PATTERN = /(?:[$€£]\s*)?\b\d[\d,.]*(?:\s*%|\s*[kKmMbB])?(?=$|[^\w])/g;
const TECHNOLOGIES = [
  "aws", "azure", "docker", "fastapi", "graphql", "java", "javascript", "kafka", "kubernetes",
  "linux", "node.js", "postgresql", "python", "react", "redis", "rust", "sql", "terraform", "typescript",
];

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (["--before", "--after", "--evidence", "--patch"].includes(argument)) {
      const value = argv[index + 1];
      if (!value) throw new Error(`${argument} requires a file path`);
      args[argument.slice(2)] = value;
      index += 1;
      continue;
    }
    if (argument === "--help" || argument === "-h") return { help: true };
    throw new Error(`Unknown option: ${argument}`);
  }
  if (!args.before || !args.after || !args.evidence || !args.patch) {
    throw new Error("Usage: verify-cv-facts.mjs --before before.json --after after.json --evidence evidence.json --patch patch.json");
  }
  return args;
}

async function readJson(path) {
  try {
    return JSON.parse(await readFile(path, "utf8"));
  } catch {
    throw new Error(`Unable to read JSON file: ${path}`);
  }
}

export function flattenText(value) {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(flattenText).join(" ");
  if (!value || typeof value !== "object") return "";
  return Object.entries(value)
    .filter(([key]) => !["id", "style", "url", "link"].includes(key))
    .map(([, child]) => flattenText(child))
    .join(" ");
}

export function normalizeNumber(value) {
  return value.replace(/[$€£\s]/g, "").replace(/,/g, "").toLowerCase();
}

function numbers(text) {
  return new Set((text.match(NUMBER_PATTERN) ?? []).map(normalizeNumber));
}

function technologies(text) {
  const lower = text.toLowerCase();
  return new Set(TECHNOLOGIES.filter((technology) => lower.includes(technology)));
}

function sectionsFromCv(cv) {
  const sections = Array.isArray(cv?.sections)
    ? cv.sections
    : Array.isArray(cv?.sections?.sections)
      ? cv.sections.sections
      : null;
  if (!sections) throw new Error("CV does not contain a sections array");
  return sections;
}

function findTarget(cv, change) {
  const section = sectionsFromCv(cv).find((candidate) => candidate?.id === change.section_id);
  if (!section) return undefined;
  if (section.type === "profile") return section.data;
  return Array.isArray(section.data)
    ? section.data.find((entry) => entry?.id === change.entry_id)
    : undefined;
}

function readField(value, fieldPath) {
  return fieldPath.split(".").reduce((current, part) => (
    current && typeof current === "object" ? current[part] : undefined
  ), value);
}

function evidenceTextForChange(evidence, change, beforeCv) {
  const target = findTarget(beforeCv, change);
  const values = [target?.[change.field ?? "description"]];
  for (const reference of change.evidence ?? []) {
    if (reference.source === "cv") {
      const section = sectionsFromCv(evidence.cv).find((candidate) => candidate?.id === reference.section_id);
      const source = section?.type === "profile"
        ? section.data
        : section?.data?.find((entry) => entry?.id === reference.entry_id);
      values.push(readField(source, reference.field_path));
      continue;
    }
    const libraryEntry = (evidence.library ?? []).find((entry) => entry?.id === reference.library_entry_id);
    const sourceRow = libraryEntry?.payload?.find((row) => row?.id === reference.source_row_id);
    values.push(readField(sourceRow, reference.field_path));
  }
  return values.map(flattenText).join(" ");
}

export function verifyFacts(before, after, evidence, patch) {
  const findings = [];
  for (const change of patch.changes ?? []) {
    if (!["replace_description", "replace_rich_text", "rewrite_rich_text"].includes(change.operation)) continue;
    const beforeTarget = findTarget(before, change)?.[change.field ?? "description"];
    const afterTarget = findTarget(after, change)?.[change.field ?? "description"];
    const beforeText = flattenText(beforeTarget);
    const afterText = flattenText(afterTarget);
    const allowedText = evidenceTextForChange(evidence, change, before);
    for (const value of numbers(afterText)) {
      if (numbers(beforeText).has(value) || numbers(allowedText).has(value)) continue;
      findings.push({ type: "number", value, status: "fail", message: `New numeric claim is not supported: ${value}` });
    }
    for (const technology of technologies(afterText)) {
      if (technologies(beforeText).has(technology) || technologies(allowedText).has(technology)) continue;
      findings.push({ type: "technology", value: technology, status: "fail", message: `New technology claim is not supported: ${technology}` });
    }
  }
  return {
    status: findings.length === 0 ? "pass" : "fail",
    findings,
    inspected_sources: { current_cv: true, cited_library: citedLibraryIds(patch) },
  };
}

function citedLibraryIds(patch) {
  return [...new Set(
    patch.changes.flatMap((change) => change.evidence ?? [])
      .filter((reference) => reference.source === "library")
      .map((reference) => reference.library_entry_id),
  )];
}

function printHelp() {
  console.log("Usage: verify-cv-facts.mjs --before before.json --after after.json --evidence evidence.json --patch patch.json");
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
      printHelp();
    } else {
      const result = verifyFacts(
        await readJson(args.before),
        await readJson(args.after),
        await readJson(args.evidence),
        await readJson(args.patch),
      );
      console.log(JSON.stringify(result, null, 2));
      if (result.status === "fail") process.exitCode = 1;
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : "Fact verification failed");
    process.exitCode = 1;
  }
}
