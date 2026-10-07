#!/usr/bin/env node

import { access, chmod, lstat, mkdir, open, readdir, readFile, unlink, writeFile } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { createHash, randomUUID } from "node:crypto";
import { StringDecoder } from "node:string_decoder";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { freezeFitReview, prepareReviewPackage, readFitReviewReport } from "./fit-review.mjs";

export const PROTOCOL_VERSION = 10;
const SUBMIT_MARKER = "SUBMIT";
const RENDER_MARKER = "RENDER";
const REVIEW_MARKER = "REVIEW";
const IDEAL_TARGET_FILE = "ideal-target.md";
const MAX_IDEAL_TARGET_BYTES = 1_048_576;
const STAGE_ZERO_JOB_FIELDS = ["company", "role", "job_url", "description", "user_instructions"];
const TAILORING_ERROR_CODES = new Set([
  "session_in_progress",
  "stale_target",
  "edited_draft",
  "preview_in_progress",
  "preview_limit",
  "quota",
  "inactive_capability",
  "invalid_session",
  "context_mismatch",
  "reservation_expired",
  "reservation_conflict",
  "request_id_reused",
  "candidate_invalid",
  "evaluation_mismatch",
  "draft_unavailable",
  "review_not_current",
  "source_changed",
  "application_unavailable",
]);
const SHA256_PATTERN = /^[0-9a-f]{64}$/;
const EVALUATION_ID_PATTERN = /^[A-Za-z0-9_-]{16,128}$/;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

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

function sessionLinkFromUrl(value) {
  let session;
  try {
    session = new URL(value);
  } catch {
    throw new Error("The tailoring session URL is invalid");
  }
  if (!["http:", "https:"].includes(session.protocol) || !session.hostname || session.username || session.password) {
    throw new Error("The tailoring session must use a safe HTTP(S) URL");
  }
  const match = /^\/agent\/tailor\/([^/]+)\/?$/.exec(session.pathname);
  if (!match) {
    throw new Error("The URL is not an Aergia tailoring session link");
  }
  let sessionId;
  try {
    sessionId = decodeURIComponent(match[1]);
  } catch {
    throw new Error("The URL is not an Aergia tailoring session link");
  }
  if (!sessionId.trim() || sessionId.includes("/") || sessionId === "." || sessionId === "..") {
    throw new Error("The URL is not an Aergia tailoring session link");
  }
  return { origin: session.origin, sessionId };
}

export function serverOriginFromSessionUrl(value) {
  return sessionLinkFromUrl(value).origin;
}

async function requestJson(url, options = {}) {
  let response;
  const { timeoutMs = 30_000, ...fetchOptions } = options;
  try {
    response = await fetch(url, {
      redirect: "error",
      signal: AbortSignal.timeout(timeoutMs),
      ...fetchOptions,
    });
  } catch {
    const error = new Error("The server could not be reached");
    error.failureKind = "transport";
    throw error;
  }
  if (!response.ok) {
    let body;
    try {
      body = await response.json();
    } catch {
      // Do not echo arbitrary remote response bodies.
    }
    const code = TAILORING_ERROR_CODES.has(body?.code) ? body.code : undefined;
    const failureKind = classifyHttpFailure(response.status, code);
    const error = new Error(safeHttpErrorMessage(response.status, failureKind, code));
    error.status = response.status;
    error.code = code;
    error.failureKind = failureKind;
    throw error;
  }
  return response.json();
}

function classifyHttpFailure(status, code) {
  if ([401, 403, 410].includes(status) || code === "inactive_capability") return "access";
  if (["stale_target", "context_mismatch"].includes(code)) return "stale";
  if (code === "preview_limit") return "preview_limit";
  if (["preview_in_progress", "reservation_expired", "reservation_conflict"].includes(code)) return "reservation";
  if (code === "candidate_invalid") return "candidate";
  if (status === 429 || status >= 500) return "transient";
  return "candidate";
}

function safeHttpErrorMessage(status, failureKind, code) {
  if (failureKind === "access") return "Tailoring access expired or was revoked";
  if (failureKind === "stale") return "The tailoring target changed; start a new session";
  if (failureKind === "preview_limit") return "The candidate-preview resource limit has been reached";
  if (failureKind === "reservation") {
    if (code === "preview_in_progress") return "A preview is already in progress for this session";
    if (code === "reservation_expired") return "The preview reservation expired and can be reacquired";
    return "The preview reservation is temporarily unavailable";
  }
  if (failureKind === "transient") return `The server returned HTTP ${status}`;
  return `The server rejected the request with HTTP ${status}`;
}

function readCode() {
  const input = process.stdin;
  const interactive = Boolean(input.isTTY && typeof input.setRawMode === "function");
  const originalRawMode = Boolean(input.isRaw);
  const decoder = new StringDecoder("utf8");

  return new Promise((resolveCode, rejectCode) => {
    let value = "";
    let settled = false;

    const cleanup = () => {
      input.off("data", onData);
      input.off("end", onEnd);
      input.off("error", onError);
      process.off("SIGINT", onInterrupt);
      input.pause();
      if (interactive && Boolean(input.isRaw) !== originalRawMode) input.setRawMode(originalRawMode);
    };

    const finish = (error, code) => {
      if (settled) return;
      settled = true;
      let cleanupError;
      try {
        cleanup();
      } catch {
        cleanupError = new Error("The terminal input mode could not be restored");
      }
      process.stderr.write("\n");
      if (error || cleanupError) {
        rejectCode(error ?? cleanupError);
        return;
      }
      try {
        resolveCode(validateCode(code));
      } catch (validationError) {
        rejectCode(validationError);
      }
    };

    const finishCurrentValue = () => finish(null, value);
    const onData = (chunk) => {
      const text = decoder.write(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk)));
      for (const character of text) {
        if (character === "\u0003") {
          finish(new Error("Reading the one-time code was interrupted"));
          return;
        }
        if (character === "\u0004") {
          finishCurrentValue();
          return;
        }
        if (character === "\n" || character === "\r") {
          finishCurrentValue();
          return;
        }
        if (character === "\b" || character === "\u007f") {
          value = Array.from(value).slice(0, -1).join("");
          continue;
        }
        value += character;
      }
    };
    const onEnd = () => finishCurrentValue();
    const onError = () => finish(new Error("The one-time code could not be read from stdin"));
    const onInterrupt = () => finish(new Error("Reading the one-time code was interrupted"));

    try {
      if (interactive && !originalRawMode) input.setRawMode(true);
      input.on("data", onData);
      input.once("end", onEnd);
      input.once("error", onError);
      process.once("SIGINT", onInterrupt);
      process.stderr.write("One-time session code: ");
      input.resume();
    } catch {
      try {
        cleanup();
      } catch {
        // The original setup error is safer and more useful than terminal details.
      }
      rejectCode(new Error("The one-time code could not be read from stdin"));
    }
  });
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

async function writeProtectedBinary(path, bytes) {
  await writeFile(path, bytes, { flag: "wx", mode: 0o600 });
  await chmod(path, 0o400);
}

async function replaceProtectedBinary(path, bytes) {
  await chmod(path, 0o600).catch(() => undefined);
  await writeFile(path, bytes, { mode: 0o600 });
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
  if (typeof preview.pdf_base64 !== "string" || !preview.pdf_base64
    || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(preview.pdf_base64)) {
    throw new Error("The server preview did not return a valid PDF");
  }
  if (!preview.evaluation || typeof preview.evaluation !== "object") throw new Error("The server preview did not return a tailoring evaluation");
  if (preview.evaluation.version !== "tailoring-evaluation-v2") throw new Error("The server returned an incompatible tailoring evaluation");
  if (typeof preview.evaluation_id !== "string" || !EVALUATION_ID_PATTERN.test(preview.evaluation_id)) {
    throw new Error("The server returned an invalid evaluation ID");
  }
  if (typeof preview.candidate_hash !== "string" || !SHA256_PATTERN.test(preview.candidate_hash)
    || preview.evaluation.candidate_hash !== preview.candidate_hash) {
    throw new Error("The server evaluation is bound to a different candidate");
  }
  if (typeof preview.pdf_sha256 !== "string" || !SHA256_PATTERN.test(preview.pdf_sha256)) {
    throw new Error("The server returned an invalid PDF digest");
  }
  const pdfBytes = Buffer.from(preview.pdf_base64, "base64");
  if (pdfBytes.length === 0 || pdfBytes.toString("base64") !== preview.pdf_base64
    || createHash("sha256").update(pdfBytes).digest("hex") !== preview.pdf_sha256) {
    throw new Error("The server PDF bytes do not match their saved digest");
  }
  return { ...preview, pdfBytes };
}

async function renderCandidate(paths, origin, capability, pendingPreview) {
  if (!pendingPreview.reservationId) {
    const reservation = await requestJson(`${origin}/api/v1/tailoring/preview-reservations`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Aergia-Tailoring-Capability": capability },
      body: JSON.stringify(pendingPreview.reservationRequest),
    });
    if (!reservation || typeof reservation !== "object" || !UUID_PATTERN.test(reservation.reservation_id ?? "")
      || !SHA256_PATTERN.test(reservation.candidate_hash ?? "")
      || typeof reservation.expires_at !== "string" || !Number.isFinite(Date.parse(reservation.expires_at))) {
      throw new Error("The server returned an invalid preview reservation");
    }
    pendingPreview.reservationId = reservation.reservation_id;
    pendingPreview.reservationCandidateHash = reservation.candidate_hash;
  }

  const preview = ensurePreview(await requestJson(`${origin}/api/v1/tailoring/preview`, {
    method: "POST",
    timeoutMs: 90_000,
    headers: { "Content-Type": "application/json", "X-Aergia-Tailoring-Capability": capability },
    body: JSON.stringify({
      context_hash: pendingPreview.reservationRequest.context_hash,
      reservation_id: pendingPreview.reservationId,
      candidate: pendingPreview.reservationRequest.candidate,
    }),
  }));
  if (preview.candidate_hash !== pendingPreview.reservationCandidateHash) {
    throw new Error("The preview does not match its reserved candidate");
  }
  const details = {
    format: preview.format,
    page_count: preview.page_count,
    evaluation_id: preview.evaluation_id,
    candidate_hash: preview.candidate_hash,
    pdf_sha256: preview.pdf_sha256,
    scanner_result: preview.scanner_result ?? null,
    evaluation: preview.evaluation,
    render_warnings: Array.isArray(preview.render_warnings) ? preview.render_warnings : [],
  };
  const attemptDirectory = resolve(paths.output, "attempts", preview.evaluation_id);
  await mkdir(attemptDirectory, { recursive: true, mode: 0o700 });
  await Promise.all([
    replaceEditableJson(resolve(paths.output, "candidate.json"), preview.candidate),
    replaceProtectedBinary(resolve(paths.output, "candidate-preview.pdf"), preview.pdfBytes),
    replaceProtectedJson(resolve(paths.output, "candidate-preview.json"), details),
    writeProtectedJson(resolve(attemptDirectory, "candidate.json"), preview.candidate),
    writeProtectedJson(resolve(attemptDirectory, "candidate-preview.json"), details),
    writeProtectedBinary(resolve(attemptDirectory, "candidate-preview.pdf"), preview.pdfBytes),
  ]);
  return {
    candidate: preview.candidate,
    candidateHash: preview.candidate_hash,
    evaluationId: preview.evaluation_id,
    preview: details,
    evaluation: preview.evaluation,
    pdfBytes: preview.pdfBytes,
  };
}

async function writeSessionStatus(paths, state) {
  await replaceProtectedJson(resolve(paths.output, "tailoring-status.json"), state);
}

function statusForHttpError(error) {
  if (Number.isInteger(error?.status)) return error.code ? `HTTP ${error.status} (${error.code})` : `HTTP ${error.status}`;
  return "network error";
}

function isAccessFailure(error) {
  return error?.failureKind === "access" || [401, 403, 410].includes(error?.status);
}

function isStaleSessionFailure(error) {
  return error?.failureKind === "stale";
}

function isPreviewLimitFailure(error) {
  return error?.failureKind === "preview_limit";
}

function isTransientFailure(error) {
  return ["transient", "transport"].includes(error?.failureKind)
    || error?.failureKind === "reservation";
}

function selectedAttemptFromSelection(selection, attempts) {
  if (!selection || typeof selection !== "object" || Array.isArray(selection)
    || Object.keys(selection).some((key) => !["evaluation_id", "candidate_hash"].includes(key))) {
    throw new Error("selection.json must contain only evaluation_id and candidate_hash");
  }
  if (typeof selection.evaluation_id !== "string" || !EVALUATION_ID_PATTERN.test(selection.evaluation_id)
    || typeof selection.candidate_hash !== "string" || !SHA256_PATTERN.test(selection.candidate_hash)) {
    throw new Error("selection.json must name a valid evaluation_id and candidate_hash");
  }
  const attempt = attempts.get(selection.evaluation_id);
  if (!attempt || attempt.candidateHash !== selection.candidate_hash) {
    throw new Error("selection.json must name a preview from this session with its matching candidate_hash");
  }
  return attempt;
}

async function readSelectedAttempt(paths, attempts) {
  const selection = JSON.parse(await readFile(resolve(paths.output, "selection.json"), "utf8"));
  return selectedAttemptFromSelection(selection, attempts);
}

function freezePreviewRequest(context, candidate) {
  return {
    reservationRequest: Object.freeze({
      context_hash: context.context_hash,
      candidate: structuredClone(candidate),
      request_id: randomUUID(),
    }),
    reservationId: null,
    reservationCandidateHash: null,
  };
}

async function releasePreviewReservation(origin, capability, reservationId) {
  if (!reservationId) return;
  const response = await requestJson(`${origin}/api/v1/tailoring/preview-reservations/${reservationId}/release`, {
    method: "POST",
    headers: { "X-Aergia-Tailoring-Capability": capability },
  });
  if (!["released", "already_released", "completed"].includes(response?.status)) {
    throw new Error("The server returned an invalid preview-reservation release result");
  }
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
  const reviewPath = resolve(paths.output, REVIEW_MARKER);
  const reportPath = resolve(paths.output, "fit-review.json");
  const attempts = new Map();
  const reviewedEvaluationIds = new Set();
  let reviewCount = 0;
  let firstReviewCandidateHash = null;
  let pendingPreview = null;
  let pendingSubmission = null;

  await writeSessionStatus(paths, { state: "awaiting_candidate" });
  while (Date.now() < Date.parse(context.expires_at)) {
    if (await exists(reviewPath)) {
      await unlink(reviewPath).catch(() => undefined);
      try {
        const selectedAttempt = await readSelectedAttempt(paths, attempts);
        if (reviewCount >= 2) throw new Error("Only one initial PDF review and one follow-up review are allowed");
        if (reviewedEvaluationIds.has(selectedAttempt.evaluationId)) {
          throw new Error("This immutable preview already has a review package");
        }
        if (reviewCount === 1 && selectedAttempt.candidateHash === firstReviewCandidateHash) {
          throw new Error("The follow-up review needs a changed candidate_hash after a consequential CV revision");
        }
        const reviewPackage = await prepareReviewPackage({
          reviewRoot: paths.output,
          attempt: selectedAttempt,
          job: context.job,
        });
        if (reviewCount === 0) firstReviewCandidateHash = selectedAttempt.candidateHash;
        reviewCount += 1;
        reviewedEvaluationIds.add(selectedAttempt.evaluationId);
        await writeSessionStatus(paths, {
          state: "review_package_ready",
          evaluation_id: selectedAttempt.evaluationId,
          candidate_hash: selectedAttempt.candidateHash,
          pdf_sha256: selectedAttempt.preview.pdf_sha256,
          package_directory: reviewPackage.directory,
          review_guide: resolve(fileURLToPath(new URL("../references/independent-review.md", import.meta.url))),
        });
        process.stderr.write(`Independent PDF review package ready at ${reviewPackage.directory}. Delegate a fresh reviewer using ${resolve(fileURLToPath(new URL("../references/independent-review.md", import.meta.url)))}; save its bounded result to output/fit-review.json. The helper does not launch a reviewer.\n`);
      } catch (error) {
        const message = error instanceof Error ? error.message : "review package could not be prepared";
        await writeSessionStatus(paths, { state: "review_rejected", error: message });
        process.stderr.write(`PDF review request rejected: ${message}\n`);
      }
      continue;
    }

    if (await exists(renderPath)) {
      await unlink(renderPath).catch(() => undefined);
      if (pendingPreview?.releaseRequired) {
        try {
          await releasePreviewReservation(origin, capability, pendingPreview.reservationId);
          const message = pendingPreview.releaseRequired;
          pendingPreview = null;
          await writeSessionStatus(paths, { state: "candidate_or_preview_error", error: message });
          process.stderr.write(`The failed preview reservation is released. Review candidate.json and create RENDER when it is ready.\n`);
        } catch (error) {
          const message = error instanceof Error ? error.message : "preview reservation release failed";
          if (isAccessFailure(error)) {
            await writeSessionStatus(paths, { state: "access_expired_or_revoked", error: message });
            throw new Error(message);
          }
          if (isStaleSessionFailure(error)) {
            await writeSessionStatus(paths, { state: "context_stale", error: message });
            throw new Error(`${message}. Start a new tailoring session.`);
          }
          await writeSessionStatus(paths, { state: "preview_recoverable_error", error: `${statusForHttpError(error)}: ${message}` });
          process.stderr.write(`Could not release the failed preview reservation. Retry with the same frozen candidate by creating RENDER.\n`);
        }
        continue;
      }
      if (attempts.size >= 5 && !pendingPreview) {
        await writeSessionStatus(paths, {
          state: "preview_limit_reached",
          available_previews: [...attempts.values()].map((attempt) => ({
            evaluation_id: attempt.evaluationId,
            candidate_hash: attempt.candidateHash,
          })),
        });
        process.stderr.write("The five successful preview limit has been reached. Select a saved preview or submit one already selected.\n");
        continue;
      }
      try {
        if (!pendingPreview) {
          const candidate = JSON.parse(await readFile(resolve(paths.output, "candidate.json"), "utf8"));
          pendingPreview = freezePreviewRequest(context, candidate);
        }
        const attempt = await renderCandidate(paths, origin, capability, pendingPreview);
        if (attempts.has(attempt.evaluationId)) throw new Error("The server returned a duplicate evaluation ID");
        attempts.set(attempt.evaluationId, attempt);
        pendingPreview = null;
        await writeSessionStatus(paths, {
          state: "awaiting_revision_or_selection",
          evaluation_id: attempt.evaluationId,
          candidate_hash: attempt.candidateHash,
          successful_previews: attempts.size,
        });
        process.stderr.write(`Preview ready. Review candidate-preview.pdf and candidate-preview.json, then edit candidate.json and create RENDER for another preview, or select a preview. Successful previews: ${attempts.size}/5. Current evaluation_id: ${attempt.evaluationId}; candidate_hash: ${attempt.candidateHash}.\n`);
      } catch (error) {
        const message = error instanceof Error ? error.message : "preview failed";
        if (isAccessFailure(error)) {
          await writeSessionStatus(paths, { state: "access_expired_or_revoked", error: message });
          throw new Error(message);
        }
        if (isStaleSessionFailure(error)) {
          await writeSessionStatus(paths, { state: "context_stale", error: message });
          process.stderr.write(`This tailoring session is stale: ${message}. Start a new tailoring session.\n`);
          throw new Error(`This tailoring session is stale: ${message}. Start a new tailoring session.`);
        }
        if (isPreviewLimitFailure(error)) {
          try {
            await releasePreviewReservation(origin, capability, pendingPreview?.reservationId);
          } catch (releaseError) {
            if (isAccessFailure(releaseError)) {
              await writeSessionStatus(paths, { state: "access_expired_or_revoked", error: releaseError.message });
              throw new Error(releaseError.message);
            }
          }
          pendingPreview = null;
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
        if (isTransientFailure(error)) {
          if (error?.code === "reservation_expired" && pendingPreview) {
            pendingPreview.reservationId = null;
            pendingPreview.reservationCandidateHash = null;
          }
          await writeSessionStatus(paths, {
            state: "preview_recoverable_error",
            error: `${statusForHttpError(error)}: ${message}`,
            retry_request_id: pendingPreview?.reservationRequest.request_id,
          });
          process.stderr.write(`Preview ${statusForHttpError(error)}: ${message}. Keep the frozen candidate unchanged and create RENDER to retry this same request. Lease or in-progress conflicts do not require candidate edits.\n`);
          continue;
        }
        const candidateInputError = error?.code === "candidate_invalid" || error?.status === 422;
        if (pendingPreview?.reservationId) {
          pendingPreview.releaseRequired = message;
          try {
            await releasePreviewReservation(origin, capability, pendingPreview.reservationId);
            pendingPreview = null;
          } catch (releaseError) {
            if (isAccessFailure(releaseError)) {
              await writeSessionStatus(paths, { state: "access_expired_or_revoked", error: releaseError.message });
              throw new Error(releaseError.message);
            }
            if (isStaleSessionFailure(releaseError)) {
              await writeSessionStatus(paths, { state: "context_stale", error: releaseError.message });
              throw new Error(`${releaseError.message}. Start a new tailoring session.`);
            }
            await writeSessionStatus(paths, {
              state: "preview_recoverable_error",
              error: `${statusForHttpError(releaseError)}: preview reservation release failed`,
            });
            process.stderr.write("The preview failed and its reservation could not yet be released. Create RENDER to retry release with the same request identity.\n");
            continue;
          }
        } else {
          pendingPreview = null;
        }
        await writeSessionStatus(paths, {
          state: candidateInputError ? "candidate_or_preview_error" : "preview_rejected",
          error: message,
        });
        process.stderr.write(candidateInputError
          ? `The server rejected the candidate (${statusForHttpError(error)}): ${message}. Repair candidate.json and create RENDER for a new request.\n`
          : `Preview request rejected: ${message}. Review the error and create RENDER only if the candidate itself needs a change.\n`);
      }
      continue;
    }

    if (await exists(submitPath)) {
      await unlink(submitPath).catch(() => undefined);
      if (!pendingSubmission) {
        try {
          const selectedAttempt = await readSelectedAttempt(paths, attempts);
          const fitReview = freezeFitReview(await readFitReviewReport(reportPath, {
            evaluation_id: selectedAttempt.evaluationId,
            candidate_hash: selectedAttempt.candidateHash,
            pdf_sha256: selectedAttempt.preview.pdf_sha256,
          }));
          if (!fitReview) throw new Error("fit-review.json must contain a matching completed, unavailable, or explicitly skipped report before submission");
          const reviewNotes = await readReviewNotes(paths.output);
          const selectedSubmission = {
            evaluationId: selectedAttempt.evaluationId,
            candidateHash: selectedAttempt.candidateHash,
            candidate: selectedAttempt.candidate,
            reviewNotes,
            fitReview,
          };
          const requestBody = {
            context_hash: context.context_hash,
            evaluation_id: selectedAttempt.evaluationId,
            candidate_hash: selectedAttempt.candidateHash,
            candidate: selectedAttempt.candidate,
            ...(reviewNotes.length ? { review_notes: reviewNotes } : {}),
            ...(fitReview ? { fit_review: fitReview } : {}),
          };
          pendingSubmission = {
            selected: selectedSubmission,
            requestBody,
            serializedBody: JSON.stringify(requestBody),
          };
        } catch (error) {
          const message = error instanceof Error ? error.message : "submission selection is invalid";
          await writeSessionStatus(paths, { state: "submit_rejected", error: message });
          process.stderr.write(`Submission selection rejected: ${message}\n`);
          continue;
        }
      }

      const submission = pendingSubmission;
      try {
        const result = await submitWithBackoff(`${origin}/api/v1/tailoring/submit`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Aergia-Tailoring-Capability": capability },
          body: submission.serializedBody,
        }, context.expires_at);
        if (result.protocol_version !== PROTOCOL_VERSION) throw new Error("The server returned an incompatible tailoring submit protocol");
        if (result.candidate_hash !== submission.selected.candidateHash
          || result.evaluation_id !== submission.selected.evaluationId
          || result.evaluation?.candidate_hash !== submission.selected.candidateHash) {
          throw new Error("The submitted draft did not match the selected frozen evaluation");
        }
        await writeFile(resolve(paths.output, "result.json"), `${JSON.stringify(result, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
        await writeSessionStatus(paths, {
          state: "submitted",
          evaluation_id: result.evaluation_id,
          draft_cv_id: result.draft_cv_id,
          candidate_hash: result.candidate_hash,
          fit_review_status: submission.selected.fitReview?.status ?? "not_run",
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
            evaluation_id: submission.selected.evaluationId,
            candidate_hash: submission.selected.candidateHash,
            error: `${statusForHttpError(error)}: ${message}`,
          });
          throw new Error(`${statusForHttpError(error)}: ${message}. Start a new tailoring session.`);
        }
        const transient = isTransientFailure(error);
        if (!transient) pendingSubmission = null;
        await writeSessionStatus(paths, {
          state: transient ? "submit_recoverable_error" : "submit_rejected",
          evaluation_id: submission.selected.evaluationId,
          candidate_hash: submission.selected.candidateHash,
          fit_review_status: submission.selected.fitReview?.status ?? "not_run",
          error: `${statusForHttpError(error)}: ${message}`,
        });
        process.stderr.write(`Submit ${statusForHttpError(error)}: ${message}. Recreate SUBMIT to retry the frozen selected candidate and fit-review report.\n`);
      }
      continue;
    }

    await wait(250);
  }
  await writeSessionStatus(paths, { state: "session_expired", error: "The tailoring session expired before submission completed" });
  throw new Error("The tailoring session expired before submission completed");
}

export async function runSession(sessionUrl, workspace, options = {}) {
  const { origin, sessionId } = sessionLinkFromUrl(sessionUrl);
  const paths = await prepareWorkspace(workspace);
  const code = options.code === undefined ? await readCode() : validateCode(options.code);
  const exchange = await requestJson(`${origin}/api/v1/tailoring/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ protocol_version: PROTOCOL_VERSION, session_id: sessionId, code }),
  });
  if (exchange.session_id !== sessionId) throw new Error("The one-time code does not belong to the session in this link");
  if (exchange.protocol_version !== PROTOCOL_VERSION || typeof exchange.capability !== "string" || !exchange.capability) {
    throw new Error("The server returned an incompatible tailoring protocol");
  }
  const capability = exchange.capability;
  const headers = { "X-Aergia-Tailoring-Capability": capability };
  const context = await requestJson(`${origin}/api/v1/tailoring/context`, { headers });
  if (context.session_id !== sessionId) throw new Error("The returned context does not belong to the session in this link");
  if (context.protocol_version !== PROTOCOL_VERSION || context.evaluation_version !== "tailoring-evaluation-v2"
    || typeof context.context_hash !== "string" || !/^[0-9a-f]{64}$/.test(context.context_hash)
    || typeof context.expires_at !== "string" || !Number.isFinite(Date.parse(context.expires_at))
    || !context.job || typeof context.job !== "object"
    || !Array.isArray(context.templates) || !context.capabilities || typeof context.capabilities !== "object"
    || typeof context.dossier !== "string" || !context.dossier.trim()) {
    throw new Error("The server returned an incompatible protocol v10 tailoring context");
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
