#!/usr/bin/env node

import { createInterface } from "node:readline/promises";
import { access, chmod, lstat, mkdir, open, readdir, readFile, rm, unlink, writeFile } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const PROTOCOL_VERSION = 9;
const SUBMIT_MARKER = "SUBMIT";
const RENDER_MARKER = "RENDER";
const IDEAL_TARGET_FILE = "ideal-target.md";
const MAX_IDEAL_TARGET_BYTES = 1_048_576;
const STAGE_ZERO_JOB_FIELDS = ["company", "role", "job_url", "description", "user_instructions"];

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
      if (typeof body?.detail === "string") detail = body.detail.replace(/\s+/g, " ").slice(0, 500);
      else if (Array.isArray(body?.detail)) {
        const summaries = body.detail.slice(0, 8).map((item) => {
          const location = Array.isArray(item?.loc)
            ? item.loc.filter((part) => part !== "body").map((part) => String(part).slice(0, 80)).join(".")
            : "request";
          const message = typeof item?.msg === "string" ? item.msg.replace(/\s+/g, " ").slice(0, 160) : "invalid request";
          return `${location || "request"}: ${message}`;
        });
        if (summaries.length) detail = summaries.join("; ").slice(0, 500);
      }
    } catch {
      // Do not echo arbitrary remote response bodies.
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
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

async function replaceProtectedJson(path, value) {
  await chmod(path, 0o600).catch(() => undefined);
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  await chmod(path, 0o400);
}

async function replaceEditableJson(path, value) {
  await chmod(path, 0o600).catch(() => undefined);
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  await chmod(path, 0o600);
}

async function assertEmptyWorkspace(workspace) {
  async function walk(directory) {
    let entries;
    try {
      entries = await readdir(directory, { withFileTypes: true });
    } catch (error) {
      if (error?.code === "ENOENT") return;
      throw error;
    }
    for (const entry of entries) {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) await walk(path);
      else throw new Error("Tailoring requires an empty workspace so unrelated or stale files cannot enter the session");
    }
  }
  await walk(workspace);
}

async function prepareWorkspace(workspace) {
  await assertEmptyWorkspace(workspace);
  const evidence = resolve(workspace, "evidence");
  const output = resolve(workspace, "output");
  await Promise.all([evidence, output].map((path) => mkdir(path, { recursive: true, mode: 0o700 })));
  return { evidence, output, workspace };
}

async function exposeComposerWorkspace(paths, context) {
  await writeProtectedJson(resolve(paths.evidence, "context.json"), context);
}

async function exposeJobOnlyWorkspace(paths, context) {
  const job = Object.fromEntries(STAGE_ZERO_JOB_FIELDS
    .filter((field) => Object.hasOwn(context.job, field))
    .map((field) => [field, context.job[field]]));
  await writeProtectedJson(resolve(paths.evidence, "job.json"), job);
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
  if (!Array.isArray(notes) || notes.length > 20) throw new Error("review-notes.json must be an array of at most 20 strings");
  return notes.map((note) => {
    if (typeof note !== "string" || !note.trim() || Array.from(note.trim()).length > 1_000) {
      throw new Error("Each review note must be a non-empty string of at most 1000 characters");
    }
    return note.trim();
  });
}

function wait(milliseconds) {
  return new Promise((accept) => setTimeout(accept, milliseconds));
}

async function inspectIdealTarget(path) {
  let before;
  try {
    before = await lstat(path);
  } catch (error) {
    if (error?.code === "ENOENT") return { ready: false, reason: null };
    throw error;
  }

  if (!before.isFile()) return { ready: false, reason: `${IDEAL_TARGET_FILE} must be a regular file` };
  if (before.size === 0) return { ready: false, reason: `${IDEAL_TARGET_FILE} must not be empty` };
  if (before.size > MAX_IDEAL_TARGET_BYTES) {
    return { ready: false, reason: `${IDEAL_TARGET_FILE} must be no larger than ${MAX_IDEAL_TARGET_BYTES} bytes` };
  }

  let handle;
  try {
    handle = await open(path, fsConstants.O_RDONLY | fsConstants.O_NOFOLLOW);
  } catch (error) {
    if (error?.code === "ENOENT") return { ready: false, reason: null };
    if (error?.code === "ELOOP") return { ready: false, reason: `${IDEAL_TARGET_FILE} must be a regular file` };
    throw error;
  }
  try {
    const opened = await handle.stat();
    if (!opened.isFile()) return { ready: false, reason: `${IDEAL_TARGET_FILE} must be a regular file` };
    if (opened.size === 0) return { ready: false, reason: `${IDEAL_TARGET_FILE} must not be empty` };
    if (opened.size > MAX_IDEAL_TARGET_BYTES) {
      return { ready: false, reason: `${IDEAL_TARGET_FILE} must be no larger than ${MAX_IDEAL_TARGET_BYTES} bytes` };
    }

    const buffer = Buffer.alloc(opened.size + 1);
    let bytesRead = 0;
    while (bytesRead < buffer.byteLength) {
      const result = await handle.read(buffer, bytesRead, buffer.byteLength - bytesRead, bytesRead);
      if (result.bytesRead === 0) break;
      bytesRead += result.bytesRead;
    }
    const contents = buffer.subarray(0, bytesRead);
    const after = await handle.stat();
    let pathAfter;
    try {
      pathAfter = await lstat(path);
    } catch (error) {
      if (error?.code === "ENOENT") return { ready: false, reason: null };
      throw error;
    }
    if (!after.isFile() || !pathAfter.isFile() || before.dev !== opened.dev || before.ino !== opened.ino
      || opened.dev !== after.dev || opened.ino !== after.ino || opened.dev !== pathAfter.dev || opened.ino !== pathAfter.ino
      || before.size !== opened.size || opened.size !== after.size || contents.byteLength !== after.size
      || before.mtimeMs !== opened.mtimeMs || opened.mtimeMs !== after.mtimeMs
      || before.ctimeMs !== opened.ctimeMs || opened.ctimeMs !== after.ctimeMs) {
      return { ready: false, reason: `${IDEAL_TARGET_FILE} changed while it was being checked; atomically rename a complete file into place` };
    }
    if (!contents.toString("utf8").trim()) return { ready: false, reason: `${IDEAL_TARGET_FILE} must not be blank` };
    return { ready: true, reason: null };
  } finally {
    await handle.close();
  }
}

async function waitForIdealTarget(paths, context) {
  const targetPath = resolve(paths.output, IDEAL_TARGET_FILE);
  let lastReportedReason;
  await writeSessionStatus(paths, { state: "awaiting_ideal_target" });
  process.stderr.write(`Write a complete fictional CV for this job to ${targetPath}, using ${resolve(paths.evidence, "job.json")} only. Atomically rename the completed file to ${IDEAL_TARGET_FILE}; the full candidate history will be exposed after it is ready.\n`);

  while (Date.now() < Date.parse(context.expires_at)) {
    const target = await inspectIdealTarget(targetPath);
    if (target.ready && Date.now() < Date.parse(context.expires_at)) return;
    if (target.reason && target.reason !== lastReportedReason) {
      lastReportedReason = target.reason;
      await writeSessionStatus(paths, { state: "ideal_target_invalid", error: target.reason });
      process.stderr.write(`${target.reason}. Repair the file or atomically replace it with the complete ideal target.\n`);
    } else if (!target.reason && lastReportedReason) {
      lastReportedReason = undefined;
      await writeSessionStatus(paths, { state: "awaiting_ideal_target" });
    }
    await wait(250);
  }
  await writeSessionStatus(paths, { state: "session_expired", error: "The tailoring session expired before the ideal target was completed" });
  throw new Error("The tailoring session expired before the ideal target was completed");
}

function ensurePreview(preview) {
  if (!preview || typeof preview !== "object" || Array.isArray(preview)) throw new Error("The server returned an invalid candidate preview");
  if (!preview.candidate || typeof preview.candidate !== "object" || Array.isArray(preview.candidate)) {
    throw new Error("The server preview did not return its canonical candidate");
  }
  if (typeof preview.pdf_base64 !== "string" || !preview.pdf_base64) throw new Error("The server preview did not return a PDF");
  if (!preview.evaluation || typeof preview.evaluation !== "object") throw new Error("The server preview did not return a tailoring evaluation");
  if (preview.evaluation.version !== "tailoring-evaluation-v2") throw new Error("The server returned an incompatible tailoring evaluation");
  if (typeof preview.evaluation_id !== "string" || !/^[A-Za-z0-9_-]{16,128}$/.test(preview.evaluation_id)) {
    throw new Error("The server returned an invalid evaluation ID");
  }
  if (typeof preview.candidate_hash !== "string" || !/^[0-9a-f]{64}$/.test(preview.candidate_hash)
    || preview.evaluation.candidate_hash !== preview.candidate_hash) {
    throw new Error("The server evaluation is bound to a different candidate");
  }
  return preview;
}

async function renderCandidate(paths, origin, capability, context, candidate) {
  const preview = ensurePreview(await requestJson(`${origin}/api/v1/tailoring/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Aergia-Tailoring-Capability": capability },
    body: JSON.stringify({ context_hash: context.context_hash, candidate }),
  }));
  const details = {
    format: preview.format,
    page_count: preview.page_count,
    evaluation_id: preview.evaluation_id,
    candidate_hash: preview.candidate_hash,
    scanner_result: preview.scanner_result ?? null,
    evaluation: preview.evaluation,
    render_warnings: Array.isArray(preview.render_warnings) ? preview.render_warnings : [],
  };
  const attemptDirectory = resolve(paths.output, "attempts", preview.evaluation_id);
  await mkdir(attemptDirectory, { recursive: true, mode: 0o700 });
  await Promise.all([
    replaceEditableJson(resolve(paths.output, "candidate.json"), preview.candidate),
    replaceProtectedBinary(resolve(paths.output, "candidate-preview.pdf"), preview.pdf_base64),
    replaceProtectedJson(resolve(paths.output, "candidate-preview.json"), details),
    writeProtectedJson(resolve(attemptDirectory, "candidate.json"), preview.candidate),
    writeProtectedJson(resolve(attemptDirectory, "candidate-preview.json"), details),
    writeProtectedBinary(resolve(attemptDirectory, "candidate-preview.pdf"), preview.pdf_base64),
  ]);
  return {
    candidate: preview.candidate,
    candidateHash: preview.candidate_hash,
    evaluationId: preview.evaluation_id,
    preview: details,
    evaluation: preview.evaluation,
  };
}

async function writeSessionStatus(paths, state) {
  await replaceProtectedJson(resolve(paths.output, "tailoring-status.json"), state);
}

function statusForHttpError(error) {
  return Number.isInteger(error?.status) ? `HTTP ${error.status}` : "network error";
}

function isAccessFailure(error) {
  return [401, 403, 410].includes(error?.status)
    || /expired|revoked|capability is no longer active/i.test(error?.message ?? "");
}

function isStaleSessionFailure(error) {
  return error?.status === 409
    && /context changed|contract changed|start a new (?:tailoring )?session|session protocol is no longer supported|predates protocol|older protocol/i.test(error?.message ?? "");
}

function isPreviewLimitFailure(error) {
  return error?.status === 409 && /candidate-preview resource limit has been reached/i.test(error?.message ?? "");
}

async function submitWithBackoff(url, options, expiresAt) {
  const delays = [500, 1_500, 3_000];
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await requestJson(url, options);
    } catch (error) {
      const retryable = error?.status === 429 || error?.status >= 500 || error?.status === undefined;
      if (!retryable || attempt >= delays.length || Date.now() + delays[attempt] >= Date.parse(expiresAt)) throw error;
      process.stderr.write(`Submit ${statusForHttpError(error)}; retrying after ${delays[attempt]} ms.\n`);
      await wait(delays[attempt]);
    }
  }
}

async function waitForCandidate(paths, context, origin, capability) {
  const submitPath = resolve(paths.output, SUBMIT_MARKER);
  const renderPath = resolve(paths.output, RENDER_MARKER);
  const candidatePath = resolve(paths.output, "candidate.json");
  const selectionPath = resolve(paths.output, "selection.json");
  const attempts = new Map();

  await writeSessionStatus(paths, { state: "awaiting_candidate" });
  while (Date.now() < Date.parse(context.expires_at)) {
    if (await exists(renderPath)) {
      await unlink(renderPath).catch(() => undefined);
      try {
        const candidate = JSON.parse(await readFile(candidatePath, "utf8"));
        const attempt = await renderCandidate(paths, origin, capability, context, candidate);
        if (attempts.has(attempt.evaluationId)) throw new Error("The server returned a duplicate evaluation ID");
        attempts.set(attempt.evaluationId, attempt);
        await writeSessionStatus(paths, {
          state: "awaiting_revision_or_selection",
          evaluation_id: attempt.evaluationId,
          candidate_hash: attempt.candidateHash,
        });
        process.stderr.write(`Preview ready. Review candidate-preview.pdf and candidate-preview.json, then edit candidate.json and create RENDER for another preview, or select a preview for submission. Current evaluation_id: ${attempt.evaluationId}; candidate_hash: ${attempt.candidateHash}.\n`);
      } catch (error) {
        const message = error instanceof Error ? error.message : "preview failed";
        if (isStaleSessionFailure(error)) {
          await writeSessionStatus(paths, { state: "context_stale", error: message });
          process.stderr.write(`This tailoring session is stale: ${message}. Start a new tailoring session.\n`);
          throw new Error(`This tailoring session is stale: ${message}. Start a new tailoring session.`);
        }
        if (isPreviewLimitFailure(error)) {
          const availablePreviews = [...attempts.values()].map((attempt) => ({
            evaluation_id: attempt.evaluationId,
            candidate_hash: attempt.candidateHash,
          }));
          await writeSessionStatus(paths, {
            state: "preview_limit_reached",
            available_previews: availablePreviews,
          });
          process.stderr.write(`The server declined another preview. Select one of the ${availablePreviews.length} saved previews in output/attempts and create SUBMIT.\n`);
          continue;
        }
        await writeSessionStatus(paths, { state: "candidate_or_preview_error", error: message });
        process.stderr.write(`Candidate preview failed: ${message}. Repair candidate.json and create RENDER to try again.\n`);
      }
      continue;
    }

    if (await exists(submitPath)) {
      await unlink(submitPath).catch(() => undefined);
      let selectedAttempt;
      try {
        const selection = JSON.parse(await readFile(selectionPath, "utf8"));
        if (!selection || typeof selection !== "object" || Array.isArray(selection)
          || Object.keys(selection).some((key) => !["evaluation_id", "candidate_hash"].includes(key))) {
          throw new Error("selection.json must contain only evaluation_id and candidate_hash");
        }
        if (typeof selection.evaluation_id !== "string" || !/^[A-Za-z0-9_-]{16,128}$/.test(selection.evaluation_id)
          || typeof selection.candidate_hash !== "string" || !/^[0-9a-f]{64}$/.test(selection.candidate_hash)) {
          throw new Error("selection.json must name a valid evaluation_id and candidate_hash");
        }
        const attempt = attempts.get(selection.evaluation_id);
        if (!attempt || attempt.candidateHash !== selection.candidate_hash) {
          throw new Error("selection.json must name a preview from this session with its matching candidate_hash");
        }
        selectedAttempt = { ...attempt, reviewNotes: await readReviewNotes(paths.output) };
      } catch (error) {
        const message = error instanceof Error ? error.message : "submission selection is invalid";
        await writeSessionStatus(paths, { state: "submit_rejected", error: message });
        process.stderr.write(`Submission selection rejected: ${message}\n`);
        continue;
      }

      const requestBody = {
        context_hash: context.context_hash,
        evaluation_id: selectedAttempt.evaluationId,
        candidate_hash: selectedAttempt.candidateHash,
        candidate: selectedAttempt.candidate,
        ...(selectedAttempt.reviewNotes.length ? { review_notes: selectedAttempt.reviewNotes } : {}),
      };
      try {
        const result = await submitWithBackoff(`${origin}/api/v1/tailoring/submit`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Aergia-Tailoring-Capability": capability },
          body: JSON.stringify(requestBody),
        }, context.expires_at);
        if (result.protocol_version !== PROTOCOL_VERSION) throw new Error("The server returned an incompatible tailoring submit protocol");
        if (result.candidate_hash !== selectedAttempt.candidateHash
          || result.evaluation_id !== selectedAttempt.evaluationId
          || result.evaluation?.candidate_hash !== selectedAttempt.candidateHash) {
          throw new Error("The submitted draft did not match the selected frozen evaluation");
        }
        await writeFile(resolve(paths.output, "result.json"), `${JSON.stringify(result, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
        await writeSessionStatus(paths, {
          state: "submitted",
          evaluation_id: result.evaluation_id,
          draft_cv_id: result.draft_cv_id,
          candidate_hash: result.candidate_hash,
        });
        process.stdout.write(`${JSON.stringify(result)}\n`);
        return result;
      } catch (error) {
        if (isAccessFailure(error)) {
          const message = error instanceof Error ? error.message : "Tailoring access expired or was revoked";
          await writeSessionStatus(paths, { state: "access_expired_or_revoked", error: `${statusForHttpError(error)}: ${message}` });
          throw new Error(`${statusForHttpError(error)}: ${message}`);
        }
        const message = error instanceof Error ? error.message : "submission failed";
        if (isStaleSessionFailure(error)) {
          await writeSessionStatus(paths, {
            state: "context_stale",
            evaluation_id: selectedAttempt.evaluationId,
            candidate_hash: selectedAttempt.candidateHash,
            error: `${statusForHttpError(error)}: ${message}`,
          });
          throw new Error(`${statusForHttpError(error)}: ${message}. Start a new tailoring session.`);
        }
        const transient = error?.status === 429 || error?.status >= 500 || error?.status === undefined;
        await writeSessionStatus(paths, {
          state: transient ? "submit_recoverable_error" : "submit_rejected",
          evaluation_id: selectedAttempt.evaluationId,
          candidate_hash: selectedAttempt.candidateHash,
          error: `${statusForHttpError(error)}: ${message}`,
        });
        process.stderr.write(`Submit ${statusForHttpError(error)}: ${message}. Correct selection.json or review-notes.json if needed, then recreate SUBMIT to retry.\n`);
      }
      continue;
    }

    await wait(250);
  }
  await writeSessionStatus(paths, { state: "session_expired", error: "The tailoring session expired before submission completed" });
  throw new Error("The tailoring session expired before submission completed");
}

export async function runSession(sessionUrl, workspace, options = {}) {
  const origin = serverOriginFromSessionUrl(sessionUrl);
  const paths = await prepareWorkspace(workspace);
  const code = options.code === undefined ? await readCode() : validateCode(options.code);
  const exchange = await requestJson(`${origin}/api/v1/tailoring/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ protocol_version: PROTOCOL_VERSION, code }),
  });
  if (exchange.protocol_version !== PROTOCOL_VERSION || typeof exchange.capability !== "string" || !exchange.capability) {
    throw new Error("The server returned an incompatible tailoring protocol");
  }
  const capability = exchange.capability;
  const headers = { "X-Aergia-Tailoring-Capability": capability };
  const context = await requestJson(`${origin}/api/v1/tailoring/context`, { headers });
  if (context.protocol_version !== PROTOCOL_VERSION || context.evaluation_version !== "tailoring-evaluation-v2"
    || typeof context.context_hash !== "string" || !/^[0-9a-f]{64}$/.test(context.context_hash)
    || typeof context.expires_at !== "string" || !Number.isFinite(Date.parse(context.expires_at))
    || !context.job || typeof context.job !== "object"
    || !Array.isArray(context.templates) || !context.capabilities || typeof context.capabilities !== "object"
    || typeof context.dossier !== "string" || !context.dossier.trim()) {
    throw new Error("The server returned an incompatible protocol v9 tailoring context");
  }
  await exposeJobOnlyWorkspace(paths, context);
  await waitForIdealTarget(paths, context);
  await exposeComposerWorkspace(paths, context);
  process.stdout.write(`Complete candidate dossier and job instructions ready in ${resolve(paths.evidence, "context.json")}. Rebuild the candidate from supported evidence in that dossier, write it to ${resolve(paths.output, "candidate.json")}, then create RENDER.\n`);
  return waitForCandidate(paths, context, origin, capability);
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
