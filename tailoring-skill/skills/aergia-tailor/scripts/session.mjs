#!/usr/bin/env node

import { createInterface } from "node:readline/promises";
import { access, chmod, mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { materializeCandidate, validateCandidate } from "./validate-candidate.mjs";

const PROTOCOL_VERSION = 2;
const SUBMIT_MARKER = "SUBMIT";
const RENDER_MARKER = "RENDER";

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--session" || argument === "--workspace") {
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
  if (!args.session || !args.workspace) throw new Error("Usage: session.mjs --session URL --workspace PATH");
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
      // Never echo an arbitrary response body supplied by a remote server.
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

async function writeProtectedBinary(path, base64) {
  await writeFile(path, Buffer.from(base64, "base64"), { flag: "wx", mode: 0o600 });
  await chmod(path, 0o400);
}

async function replaceProtectedBinary(path, base64) {
  await chmod(path, 0o600).catch(() => undefined);
  await writeFile(path, Buffer.from(base64, "base64"), { mode: 0o600 });
  await chmod(path, 0o400);
}

async function prepareWorkspace(workspace, context) {
  const source = resolve(workspace, "source");
  const output = resolve(workspace, "output");
  await mkdir(source, { recursive: true, mode: 0o700 });
  await mkdir(output, { recursive: true, mode: 0o700 });
  const previous = context.previous_cv ?? {};
  await Promise.all([
    writeProtectedJson(resolve(source, "context.json"), context),
    writeProtectedJson(resolve(source, "job.json"), context.job),
    writeProtectedJson(resolve(source, "profile.json"), context.profile),
    writeProtectedJson(resolve(source, "previous-cv.json"), previous),
    writeProtectedJson(resolve(source, "library.json"), context.library ?? []),
    writeProtectedJson(resolve(source, "requirements.json"), context.requirements ?? []),
    writeProtectedJson(resolve(source, "templates.json"), context.templates ?? []),
    writeProtectedJson(resolve(source, "capabilities.json"), context.capabilities ?? {}),
    writeProtectedJson(resolve(source, "effective-appearance.json"), context.effective_appearance ?? {}),
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

async function readReviewNotes(output) {
  let source;
  try {
    source = await readFile(resolve(output, "review-notes.json"), "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
  const notes = JSON.parse(source);
  if (!Array.isArray(notes) || notes.length > 20) {
    throw new Error("review-notes.json must be an array of at most 20 strings");
  }
  return notes.map((note) => {
    if (typeof note !== "string" || !note.trim() || note.trim().length > 1_000) {
      throw new Error("Each review note must be a non-empty string of at most 1000 characters");
    }
    return note.trim();
  });
}

function wait(milliseconds) {
  return new Promise((accept) => setTimeout(accept, milliseconds));
}

async function renderCandidate(paths, origin, capability, context, candidate) {
  const preview = await requestJson(`${origin}/api/v1/tailoring/preview`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Aergia-Tailoring-Capability": capability,
    },
    body: JSON.stringify({ context_hash: context.context_hash, candidate }),
  });
  await replaceProtectedBinary(resolve(paths.output, "candidate-preview.pdf"), preview.pdf_base64);
  await writeFile(
    resolve(paths.output, "candidate-preview.json"),
    `${JSON.stringify({ format: preview.format, page_count: preview.page_count, candidate_hash: preview.candidate_hash }, null, 2)}\n`,
    { encoding: "utf8", mode: 0o600 },
  );
}

async function waitForCandidate(paths, context, origin, capability) {
  const submitPath = resolve(paths.output, SUBMIT_MARKER);
  const renderPath = resolve(paths.output, RENDER_MARKER);
  const candidatePath = resolve(paths.output, "candidate.json");
  while (Date.now() < Date.parse(context.expires_at)) {
    if (!(await exists(submitPath)) && !(await exists(renderPath))) {
      await wait(750);
      continue;
    }
    try {
      const candidate = JSON.parse(await readFile(candidatePath, "utf8"));
      validateCandidate(candidate, context);
      const reviewNotes = await readReviewNotes(paths.output);
      const normalized = materializeCandidate(candidate);
      if (await exists(renderPath)) {
        await renderCandidate(paths, origin, capability, context, normalized);
        await unlink(renderPath).catch(() => undefined);
        process.stderr.write(`Candidate rendered to ${resolve(paths.output, "candidate-preview.pdf")}\n`);
        continue;
      }
      await writeFile(resolve(paths.output, "normalized-candidate.json"), `${JSON.stringify(normalized, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
      return { candidate: normalized, reviewNotes };
    } catch (error) {
      await unlink(submitPath).catch(() => undefined);
      await unlink(renderPath).catch(() => undefined);
      process.stderr.write(`Candidate rejected locally or by preview: ${error instanceof Error ? error.message : "validation failed"}\n`);
      process.stderr.write(`Repair ${candidatePath}, then recreate ${submitPath} or ${renderPath}.\n`);
    }
  }
  throw new Error("The tailoring session expired before a valid candidate was ready");
}

export async function runSession(sessionUrl, workspace, options = {}) {
  const origin = serverOriginFromSessionUrl(sessionUrl);
  const code = options.code === undefined ? await readCode() : validateCode(options.code);
  const exchange = await requestJson(`${origin}/api/v1/tailoring/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ protocol_version: PROTOCOL_VERSION, code }),
  });
  if (exchange.protocol_version !== PROTOCOL_VERSION || typeof exchange.capability !== "string") {
    throw new Error("The server returned an incompatible tailoring protocol");
  }
  // This value never leaves the process.
  const capability = exchange.capability;
  const context = await requestJson(`${origin}/api/v1/tailoring/context`, {
    headers: { "X-Aergia-Tailoring-Capability": capability },
  });
  if (context.protocol_version !== PROTOCOL_VERSION) throw new Error("The tailoring context is incompatible with this skill");

  const paths = await prepareWorkspace(workspace, context);
  if (context.rendered_source?.endpoint) {
    try {
      const sourcePreview = await requestJson(`${origin}${context.rendered_source.endpoint}`, {
        headers: { "X-Aergia-Tailoring-Capability": capability },
      });
      await writeProtectedBinary(resolve(paths.source, "source-cv.pdf"), sourcePreview.pdf_base64);
      await writeFile(
        resolve(paths.source, "source-cv-render.json"),
        `${JSON.stringify({ format: sourcePreview.format, page_count: sourcePreview.page_count, candidate_hash: sourcePreview.candidate_hash }, null, 2)}\n`,
        { encoding: "utf8", mode: 0o600 },
      );
    } catch (error) {
      process.stderr.write(`Source PDF preview unavailable: ${error instanceof Error ? error.message : "render failed"}\n`);
    }
  }
  process.stdout.write(`Context ready in ${paths.source}\n`);
  process.stdout.write(`Write ${resolve(paths.output, "candidate.json")}, create ${resolve(paths.output, "RENDER")} to preview, then create ${resolve(paths.output, SUBMIT_MARKER)} to submit.\n`);
  const { candidate, reviewNotes } = await waitForCandidate(paths, context, origin, capability);
  const result = await requestJson(`${origin}/api/v1/tailoring/submit`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Aergia-Tailoring-Capability": capability,
    },
    body: JSON.stringify({ context_hash: context.context_hash, candidate, review_notes: reviewNotes }),
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
    if (args.help) printHelp();
    else await runSession(args.session, args.workspace);
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : "Tailoring session failed"}\n`);
    process.exitCode = 1;
  }
}
