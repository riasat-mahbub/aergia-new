#!/usr/bin/env node

import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const API_PREFIX = "/api/v1";
const DEFAULT_SERVER = process.env.AERGIA_URL || "http://localhost:8000";

export function parseArgs(argv) {
  let code = null;
  let server = DEFAULT_SERVER;
  let value = null;
  let submit = true;

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--help" || argument === "-h") {
      return { help: true };
    }
    if (argument === "--no-submit") {
      submit = false;
      continue;
    }
    if (argument === "--server") {
      server = argv[index + 1];
      index += 1;
      if (!server) throw new Error("--server requires a URL");
      continue;
    }
    if (argument === "--value") {
      value = argv[index + 1];
      index += 1;
      if (!value) throw new Error("--value requires text");
      continue;
    }
    if (argument.startsWith("-")) {
      throw new Error(`Unknown option: ${argument}`);
    }
    if (code !== null) throw new Error("Only one tailoring session code is supported");
    code = argument;
  }

  if (!code) throw new Error("Usage: aergia-tailor <session-code> [--server <url>] [--no-submit]");
  return { code, server: server.replace(/\/+$/, ""), value, submit, help: false };
}

export function buildFixedPatch(evidence, value = null) {
  const sections = Array.isArray(evidence?.cv?.sections)
    ? evidence.cv.sections
    : Array.isArray(evidence?.cv?.sections?.sections)
      ? evidence.cv.sections.sections
      : [];
  for (const section of sections) {
    if (typeof section?.id !== "string" || !Array.isArray(section?.data)) continue;
    for (const entry of section.data) {
      if (typeof entry?.id !== "string" || typeof entry.description !== "string") continue;
      const replacement = value || `${entry.description.trim()} [Aergia protocol prototype]`;
      return {
        protocol_version: 1,
        changes: [
          {
            operation: "replace_description",
            section_id: section.id,
            entry_id: entry.id,
            value: replacement,
            reason: "Fixed protocol prototype patch"
          }
        ]
      };
    }
  }
  throw new Error("Evidence packet has no plain-string description target for the fixed patch");
}

async function requestJson(server, path, options = {}) {
  const response = await fetch(`${server}${API_PREFIX}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });
  const text = await response.text();
  let body = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : `Aergia request failed (${response.status})`;
    throw new Error(detail);
  }
  return body;
}

export async function runTailoring({ code, server = DEFAULT_SERVER, value = null, submit = true }) {
  const exchange = await requestJson(server.replace(/\/+$/, ""), "/tailoring/exchange", {
    method: "POST",
    body: JSON.stringify({ protocol_version: 1, code })
  });
  const capability = exchange.capability;
  const evidence = await requestJson(server.replace(/\/+$/, ""), "/tailoring/evidence", {
    headers: { "X-Aergia-Tailoring-Capability": capability }
  });
  const patch = buildFixedPatch(evidence, value);
  if (!submit) return { evidence, patch, result: null };

  const result = await requestJson(server.replace(/\/+$/, ""), "/tailoring/submit", {
    method: "POST",
    headers: { "X-Aergia-Tailoring-Capability": capability },
    body: JSON.stringify(patch)
  });
  return { evidence, patch, result };
}

function printHelp() {
  console.log("Usage: aergia-tailor <session-code> [--server <url>] [--value <text>] [--no-submit]");
  console.log("Exchanges the code, fetches evidence, and submits the fixed Phase 1 protocol patch.");
}

async function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
      printHelp();
      return;
    }
    const result = await runTailoring(args);
    const target = result.patch.changes[0];
    console.log(`Fetched evidence for ${result.evidence.job.role} at ${result.evidence.job.company}.`);
    console.log(`Fixed patch target: ${target.section_id}/${target.entry_id}.`);
    if (!result.result) {
      console.log("Patch prepared; submission skipped.");
      return;
    }
    const score = result.result.relevance?.score;
    console.log(`Submitted protocol patch. Relevance score: ${score ?? "unavailable"}.`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : "Unable to run tailoring prototype");
    process.exitCode = 1;
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main();
}
