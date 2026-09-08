#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const KNOWN_SKILLS = [
  "aws", "azure", "docker", "fastapi", "git", "golang", "graphql", "java", "javascript",
  "kafka", "kubernetes", "linux", "node.js", "postgresql", "python", "react", "redis", "rust",
  "sql", "terraform", "typescript", "webassembly",
];

const NOISE = /^(about us|benefits|equal opportunity|eeo|what we offer|salary|compensation|apply|location|our values)\b/i;

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (["--job", "--cv", "--library", "--requirements"].includes(argument)) {
      const value = argv[index + 1];
      if (!value) throw new Error(`${argument} requires a file path`);
      args[argument.slice(2)] = value;
      index += 1;
      continue;
    }
    if (argument === "--help" || argument === "-h") return { help: true };
    throw new Error(`Unknown option: ${argument}`);
  }
  if (!args.job || !args.cv) throw new Error("Usage: jd-check.mjs --job job.json --cv cv.json [--library library.json] [--requirements requirements.json]");
  return args;
}

async function readJson(path) {
  try {
    return JSON.parse(await readFile(path, "utf8"));
  } catch {
    throw new Error(`Unable to read JSON file: ${path}`);
  }
}

function textFromValue(value) {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(textFromValue).join(" ");
  if (!value || typeof value !== "object") return "";
  return Object.entries(value)
    .filter(([key]) => !["id", "style", "url", "link"].includes(key))
    .map(([, child]) => textFromValue(child))
    .join(" ");
}

export function flattenEvidence(value) {
  return textFromValue(value).replace(/\s+/g, " ").trim();
}

function normalized(value) {
  return value.toLowerCase().replace(/[“”'’`]/g, "").replace(/[^a-z0-9+#.\s-]/g, " ").replace(/\s+/g, " ").trim();
}

function requirementSections(description) {
  const lines = description.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const inRequirementSection = lines.some((line) => /\b(requirements?|qualifications?|responsibilities|you will)\b/i.test(line));
  return lines.filter((line) => {
    if (NOISE.test(line)) return false;
    if (/^[A-Z][A-Z\s&/-]{3,60}:?$/.test(line)) return /requirements?|qualifications?|responsibilities|skills/i.test(line);
    return inRequirementSection || /\b(must|should|required|experience with|proficien|familiar|knowledge of)\b/i.test(line);
  });
}

export function checkJobDescription(job, cv, library = [], storedRequirements = []) {
  const description = typeof job?.description === "string" ? job.description : "";
  const resumeText = normalized(flattenEvidence(cv));
  const libraryText = normalized(flattenEvidence(library));
  const candidateText = requirementSections(description).join(" ");
  const sourceText = `${resumeText} ${libraryText}`;
  const discovered = KNOWN_SKILLS.filter((skill) => {
    const pattern = new RegExp(`(^|[^a-z0-9+#])${skill.replace(".", "\\.")}(?=$|[^a-z0-9+#])`, "i");
    return pattern.test(candidateText);
  });
  const candidates = Array.isArray(storedRequirements) && storedRequirements.length > 0
    ? storedRequirements.map((requirement) => ({
        id: requirement?.id,
        requirement: requirement?.text ?? requirement?.requirement ?? requirement?.canonical ?? requirement?.normalized,
        normalized: requirement?.canonical ?? requirement?.normalized ?? requirement?.text,
        required: requirement?.required,
        type: requirement?.type,
      })).filter((requirement) => typeof requirement.requirement === "string" && requirement.requirement.trim())
    : discovered.map((skill) => ({ requirement: skill, normalized: skill }));
  const requirements = candidates.map((requirement) => {
    const term = normalized(requirement.normalized);
    const existing = sourceText.includes(term);
    const supportedByResume = resumeText.includes(term);
    return {
      ...requirement,
      normalized: term,
      existing,
      supportedByResume,
      gap: !existing,
    };
  });

  return {
    requirements,
    inconclusive: !description.trim() || requirements.length === 0,
    inspected_requirement_lines: requirementSections(description).length,
  };
}

function printHelp() {
  console.log("Usage: jd-check.mjs --job job.json --cv cv.json [--library library.json] [--requirements requirements.json]");
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
      printHelp();
    } else {
      const result = checkJobDescription(
        await readJson(args.job),
        await readJson(args.cv),
        args.library ? await readJson(args.library) : [],
        args.requirements ? await readJson(args.requirements) : [],
      );
      console.log(JSON.stringify(result, null, 2));
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : "JD check failed");
    process.exitCode = 1;
  }
}
