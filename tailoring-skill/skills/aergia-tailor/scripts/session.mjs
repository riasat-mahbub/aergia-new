#!/usr/bin/env node

import { createInterface } from "node:readline/promises";
import { access, chmod, mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { materializePatch, validatePatch } from "./validate-patch.mjs";
import { verifyFacts } from "./verify-cv-facts.mjs";

const SUBMIT_MARKER = "SUBMIT";

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--session" || argument === "--workspace") {
      const value = argv[index + 1];
      if (!value) throw new Error(`${argument} requires a value`);
      args[argument.slice(2)] = value;
      index += 1;
      continue;
    }
    if (argument === "--help" || argument === "-h") return { help: true };
    throw new Error(`Unknown option: ${argument}`);
  }
  if (!args.session || !args.workspace) {
    throw new Error("Usage: session.mjs --session URL --workspace PATH");
  }
  return args;
}

export function serverOriginFromSessionUrl(value) {
  let session;
  try {
    session = new URL(value);
  } catch {
    throw new Error("The tailoring session URL is invalid");
  }
  if (!["http:", "https:"].includes(session.protocol) || !session.hostname || session.username || session.password) {
    throw new Error("The tailoring session must use a safe HTTP(S) URL");
  }
  if (!/^\/agent\/tailor\/[^/]+\/?$/.test(session.pathname)) {
    throw new Error("The URL is not an Aergia tailoring session link");
  }
  return session.origin;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    redirect: "error",
    signal: AbortSignal.timeout(30_000),
    ...options,
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // Do not echo arbitrary response bodies from a server supplied by text.
    }
    throw new Error(detail);
  }
  return response.json();
}

async function readCode() {
  const terminal = createInterface({ input: process.stdin, output: process.stderr });
  const code = (await terminal.question("One-time session code: ")).trim();
  terminal.close();
  return validateCode(code);
}

function validateCode(value) {
  const code = typeof value === "string" ? value.trim() : "";
  if (code.length < 16 || code.length > 128) throw new Error("The one-time code is invalid");
  return code;
}

async function writeProtectedJson(path, value) {
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, { encoding: "utf8", flag: "wx", mode: 0o600 });
  await chmod(path, 0o400);
}

async function prepareWorkspace(workspace, evidence) {
  const source = resolve(workspace, "source");
  const output = resolve(workspace, "output");
  await mkdir(source, { recursive: true, mode: 0o700 });
  await mkdir(output, { recursive: true, mode: 0o700 });
  await Promise.all([
    writeProtectedJson(resolve(source, "evidence.json"), evidence),
    writeProtectedJson(resolve(source, "job.json"), evidence.job),
    writeProtectedJson(resolve(source, "cv.json"), evidence.cv),
    writeProtectedJson(resolve(source, "target-cv.json"), evidence.target_cv ?? evidence.cv),
    writeProtectedJson(resolve(source, "library.json"), evidence.library ?? []),
    writeProtectedJson(resolve(source, "protected-facts.json"), evidence.protected_facts ?? {}),
    writeProtectedJson(resolve(source, "requirements.json"), evidence.requirements ?? []),
  ]);
  return { source, output };
}

async function exists(path) {
  try {
    await access(path, fsConstants.F_OK);
    return true;
  } catch {
    return false;
  }
}

function wait(milliseconds) {
  return new Promise((accept) => setTimeout(accept, milliseconds));
}

async function validatedPatch(paths, evidence) {
  const markerPath = resolve(paths.output, SUBMIT_MARKER);
  const patchPath = resolve(paths.output, "tailoring-patch.json");
  const previewPath = resolve(paths.output, "tailored-cv.json");
  while (Date.now() < Date.parse(evidence.expires_at)) {
    if (!(await exists(markerPath))) {
      await wait(750);
      continue;
    }
    try {
      const patch = JSON.parse(await readFile(patchPath, "utf8"));
      validatePatch(patch, evidence);
      const tailored = materializePatch(patch, evidence);
      const facts = verifyFacts(evidence.target_cv ?? evidence.cv, tailored, evidence, patch);
      if (facts.status !== "pass") {
        throw new Error(facts.findings.map((finding) => finding.message).join("; "));
      }
      await writeFile(previewPath, `${JSON.stringify(tailored, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
      return patch;
    } catch (error) {
      await unlink(markerPath).catch(() => undefined);
      process.stderr.write(`Patch rejected locally: ${error instanceof Error ? error.message : "validation failed"}\n`);
      process.stderr.write(`Repair ${patchPath}, inspect the evidence again, then recreate ${markerPath}.\n`);
    }
  }
  throw new Error("The tailoring session expired before a valid patch was ready");
}

export async function runSession(sessionUrl, workspace, options = {}) {
  const origin = serverOriginFromSessionUrl(sessionUrl);
  const code = options.code === undefined ? await readCode() : validateCode(options.code);
  const exchange = await requestJson(`${origin}/api/v1/tailoring/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ protocol_version: 1, code }),
  });
  if (exchange.protocol_version !== 1 || typeof exchange.capability !== "string") {
    throw new Error("The server returned an incompatible tailoring protocol");
  }

  // This value never leaves the process. The helper intentionally performs
  // evidence retrieval and final submission in one lifetime.
  const capability = exchange.capability;
  const evidence = await requestJson(`${origin}/api/v1/tailoring/evidence`, {
    headers: { "X-Aergia-Tailoring-Capability": capability },
  });
  if (evidence.protocol_version !== 1) throw new Error("The evidence protocol is incompatible with this skill");

  const paths = await prepareWorkspace(workspace, evidence);
  process.stdout.write(`Evidence ready in ${paths.source}\n`);
  process.stdout.write(`Write ${resolve(paths.output, "tailoring-patch.json")}, then create ${resolve(paths.output, SUBMIT_MARKER)} to validate and submit.\n`);
  const patch = await validatedPatch(paths, evidence);
  const result = await requestJson(`${origin}/api/v1/tailoring/submit`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Aergia-Tailoring-Capability": capability,
    },
    body: JSON.stringify(patch),
  });
  await writeFile(resolve(paths.output, "result.json"), `${JSON.stringify(result, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  process.stdout.write(`${JSON.stringify(result)}\n`);
  return result;
}

function printHelp() {
  console.log("Usage: session.mjs --session URL --workspace PATH");
  console.log("Reads the one-time code from stdin and keeps the scoped capability in process memory.");
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
      printHelp();
    } else {
      await runSession(args.session, args.workspace);
    }
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : "Tailoring session failed"}\n`);
    process.exitCode = 1;
  }
}
