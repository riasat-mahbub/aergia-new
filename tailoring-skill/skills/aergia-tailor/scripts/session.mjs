#!/usr/bin/env node

import { createInterface } from "node:readline/promises";
import { createHash } from "node:crypto";
import { access, chmod, mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { materializeCandidate, validateCandidate } from "./validate-candidate.mjs";
import {
  EDITORIAL_REVIEW_VERSION,
  MAX_EVALUATED_PASSES,
  validateEditorialReview,
  validateInferenceNotes,
} from "./validate-editorial-review.mjs";

export const PROTOCOL_VERSION = 5;
const SUBMIT_MARKER = "SUBMIT";
const RENDER_MARKER = "RENDER";
const EDITORIAL_REVIEW_MARKER = "EDITORIAL_REVIEW";

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
      // Do not echo arbitrary remote response bodies.
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

async function replaceProtectedJson(path, value) {
  await chmod(path, 0o600).catch(() => undefined);
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  await chmod(path, 0o400);
}

function sortJson(value) {
  if (Array.isArray(value)) return value.map(sortJson);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(Object.keys(value).sort().map((key) => [key, sortJson(value[key])]));
}

export function candidateInputHash(candidate) {
  return createHash("sha256").update(JSON.stringify(sortJson(candidate))).digest("hex");
}

async function prepareWorkspace(workspace, context) {
  const source = resolve(workspace, "source");
  const output = resolve(workspace, "output");
  await mkdir(source, { recursive: true, mode: 0o700 });
  await mkdir(output, { recursive: true, mode: 0o700 });
  const previous = context.previous_cv ?? {};
  const scanner = context.scanner ?? {};
  const requirementExtraction = scanner.requirement_extraction ?? {};
  await Promise.all([
    writeProtectedJson(resolve(source, "context.json"), context),
    writeProtectedJson(resolve(source, "job.json"), context.job),
    writeProtectedJson(resolve(source, "profile.json"), context.profile),
    writeProtectedJson(resolve(source, "previous-cv.json"), previous),
    writeProtectedJson(resolve(source, "library.json"), context.library ?? []),
    writeProtectedJson(resolve(source, "scanner-context.json"), scanner),
    writeProtectedJson(resolve(source, "requirements.json"), requirementExtraction.requirements ?? context.requirements ?? []),
    writeProtectedJson(resolve(source, "source-scan.json"), scanner.source_scan ?? null),
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
  if (!Array.isArray(notes) || notes.length > 20) throw new Error("review-notes.json must be an array of at most 20 strings");
  return notes.map((note) => {
    if (typeof note !== "string" || !note.trim() || note.trim().length > 1_000) {
      throw new Error("Each review note must be a non-empty string of at most 1000 characters");
    }
    return note.trim();
  });
}

async function readInferenceNotes(output) {
  let source;
  try {
    source = await readFile(resolve(output, "inference-notes.json"), "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
  return validateInferenceNotes(JSON.parse(source));
}

function wait(milliseconds) {
  return new Promise((accept) => setTimeout(accept, milliseconds));
}

function ensureEvaluation(evaluation, candidateHash) {
  if (!evaluation || typeof evaluation !== "object") throw new Error("The server preview did not return a tailoring evaluation");
  if (evaluation.version !== "tailoring-evaluation-v1") throw new Error("The server returned an incompatible tailoring evaluation");
  if (evaluation.candidate_hash !== candidateHash) throw new Error("The server evaluation is bound to a different candidate");
  if (!["ready", "ready_with_review", "revise", "blocked"].includes(evaluation.readiness?.status)) throw new Error("The server returned an invalid tailoring readiness state");
  return evaluation;
}

async function renderCandidate(paths, origin, capability, context, candidate, passNumber) {
  const candidateInputDigest = candidateInputHash(candidate);
  const inferenceNotes = await readInferenceNotes(paths.output);
  const preview = await requestJson(`${origin}/api/v1/tailoring/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Aergia-Tailoring-Capability": capability },
    body: JSON.stringify({ context_hash: context.context_hash, candidate, inference_notes: inferenceNotes }),
  });
  const evaluation = ensureEvaluation(preview.evaluation, preview.candidate_hash);
  await replaceProtectedBinary(resolve(paths.output, "candidate-preview.pdf"), preview.pdf_base64);
  const details = {
    format: preview.format,
    page_count: preview.page_count,
    candidate_hash: preview.candidate_hash,
    candidate_input_hash: candidateInputDigest,
    pass_number: passNumber,
    scanner_result: preview.scanner_result ?? null,
    evaluation,
    inference_notes: inferenceNotes,
    render_warnings: Array.isArray(preview.render_warnings) ? preview.render_warnings : [],
  };
  await replaceProtectedJson(resolve(paths.output, "candidate-preview.json"), details);
  return { candidate, candidateInputHash: candidateInputDigest, candidateHash: preview.candidate_hash, passNumber, pdfBase64: preview.pdf_base64, inferenceNotes, preview: details, evaluation };
}

async function writeSessionStatus(paths, state) {
  await replaceProtectedJson(resolve(paths.output, "tailoring-status.json"), state);
}

async function writeEditorialReviewResult(paths, result) {
  await replaceProtectedJson(resolve(paths.output, "editorial-review-result.json"), result);
}

async function appendReviewNote(notes, note) {
  return [...notes.slice(0, 19), note.slice(0, 1_000)];
}

function readinessRank(status) {
  return { blocked: 0, revise: 1, ready_with_review: 2, ready: 3 }[status] ?? 0;
}

function issueList(evaluation, key) {
  return Array.isArray(evaluation?.[key]) ? evaluation[key] : [];
}

const ISSUE_STATE_FIELDS = ["id", "kind", "category", "priority", "importance", "code", "requirement_id", "term_id"];

function issueStateSignature(items) {
  return items.map((item) => {
    if (typeof item === "string") return JSON.stringify({ id: item });
    return JSON.stringify(Object.fromEntries(ISSUE_STATE_FIELDS.map((field) => [field, item?.[field] ?? null])));
  }).sort();
}

function issueCount(evaluation) {
  return ["blockers", "review_items", "recommendations", "regressions", "non_actionable_gaps"].reduce((total, key) => total + issueList(evaluation, key).length, 0);
}

function highPriorityRecommendations(evaluation) {
  return issueList(evaluation, "recommendations").filter((item) => item?.priority === "high").length;
}

function materialRegressions(evaluation) {
  return issueList(evaluation, "regressions").filter((item) => item?.priority === "high" || item?.importance === "required").length;
}

function isBetterAttempt(current, best) {
  if (!best) return true;
  const currentStatus = current.evaluation?.readiness?.status;
  const bestStatus = best.evaluation?.readiness?.status;
  if (readinessRank(currentStatus) !== readinessRank(bestStatus)) return readinessRank(currentStatus) > readinessRank(bestStatus);
  if (issueList(current.evaluation, "blockers").length !== issueList(best.evaluation, "blockers").length) return issueList(current.evaluation, "blockers").length < issueList(best.evaluation, "blockers").length;
  if (materialRegressions(current.evaluation) !== materialRegressions(best.evaluation)) return materialRegressions(current.evaluation) < materialRegressions(best.evaluation);
  const currentErrors = issueList(current.evaluation, "blockers").filter((item) => ["pdf_recovery", "resume_quality"].includes(item?.category)).length;
  const bestErrors = issueList(best.evaluation, "blockers").filter((item) => ["pdf_recovery", "resume_quality"].includes(item?.category)).length;
  if (currentErrors !== bestErrors) return currentErrors < bestErrors;
  if (highPriorityRecommendations(current.evaluation) !== highPriorityRecommendations(best.evaluation)) return highPriorityRecommendations(current.evaluation) < highPriorityRecommendations(best.evaluation);
  if (issueCount(current.evaluation) !== issueCount(best.evaluation)) return issueCount(current.evaluation) < issueCount(best.evaluation);
  if (current.passNumber !== best.passNumber) return current.passNumber > best.passNumber;
  return current.candidateHash < best.candidateHash;
}

function actionSignature(evaluation) {
  return JSON.stringify({
    blockers: issueStateSignature(issueList(evaluation, "blockers")),
    review_items: issueStateSignature(issueList(evaluation, "review_items")),
    recommendations: issueStateSignature(issueList(evaluation, "recommendations")),
    regressions: issueStateSignature(issueList(evaluation, "regressions")),
    gaps: issueStateSignature(issueList(evaluation, "non_actionable_gaps")),
  });
}

function hasEditorialBlockingFinding(review) {
  return review?.findings?.some((finding) => finding.severity === "blocking") === true;
}

function isEligibleFallback(attempt, editorialBlockedCandidateHashes) {
  return Boolean(
    attempt
      && attempt.evaluation.readiness.status !== "blocked"
      && !editorialBlockedCandidateHashes.has(attempt.candidateHash)
      && !hasEditorialBlockingFinding(attempt.editorialReview),
  );
}

function fallbackReviewNote(attempt, passCount, stopReason) {
  const unresolved = [...issueList(attempt.evaluation, "review_items").slice(0, 3), ...issueList(attempt.evaluation, "recommendations").slice(0, 3)]
    .map((item) => typeof item === "string" ? item : item?.message).filter(Boolean);
  const reason = stopReason === "repeated_candidate" ? "the candidate hash repeated" : stopReason === "unchanged_instrumentation" ? "two revisions left the actionable server issues unchanged" : stopReason === "unchanged_blockers" ? "two revisions left the same blocking issues unresolved" : "the five-pass evaluation limit was reached";
  const remaining = unresolved.length > 0 ? unresolved.join("; ") : "review the server's remaining issue state";
  return (`Bounded tailoring review stopped after ${passCount} evaluated pass(es) because ${reason}. Remaining review: ${remaining}`).slice(0, 1_000);
}

async function waitForCandidate(paths, context, origin, capability) {
  const submitPath = resolve(paths.output, SUBMIT_MARKER);
  const renderPath = resolve(paths.output, RENDER_MARKER);
  const reviewMarkerPath = resolve(paths.output, EDITORIAL_REVIEW_MARKER);
  const candidatePath = resolve(paths.output, "candidate.json");
  const reviewFilePath = resolve(paths.output, "editorial-review.json");
  const attempts = [];
  const seenCandidateHashes = new Set();
  let latestRender = null;
  let latestReview = null;
  let bestAttempt = null;
  let passCount = 0;
  let fallbackReady = false;
  let stopReason = null;
  let unchangedActionRevisions = 0;
  let unchangedBlockerRevisions = 0;
  const editorialBlockedCandidateHashes = new Set();

  await writeSessionStatus(paths, { state: "awaiting_candidate", pass_number: 0, max_passes: MAX_EVALUATED_PASSES });
  while (Date.now() < Date.parse(context.expires_at)) {
    if (await exists(renderPath)) {
      await unlink(renderPath).catch(() => undefined);
      await unlink(reviewMarkerPath).catch(() => undefined);
      await unlink(reviewFilePath).catch(() => undefined);
      await unlink(resolve(paths.output, "editorial-review-result.json")).catch(() => undefined);
      if (passCount >= MAX_EVALUATED_PASSES) {
        fallbackReady = isEligibleFallback(bestAttempt, editorialBlockedCandidateHashes);
        stopReason = "max_passes";
        await writeSessionStatus(paths, { state: fallbackReady ? "fallback_available" : "blocked", pass_number: passCount, max_passes: MAX_EVALUATED_PASSES, stop_reason: stopReason });
        continue;
      }
      try {
        const raw = JSON.parse(await readFile(candidatePath, "utf8"));
        validateCandidate(raw, context);
        const candidate = materializeCandidate(raw);
        if (
          latestRender
          && editorialBlockedCandidateHashes.has(latestRender.candidateHash)
          && candidateInputHash(candidate) === latestRender.candidateInputHash
        ) {
          throw new Error("The candidate has an editorial blocking finding; make a material candidate revision before rendering again");
        }
        await replaceProtectedJson(resolve(paths.output, "normalized-candidate.json"), candidate);
        const passNumber = passCount + 1;
        const rendered = await renderCandidate(paths, origin, capability, context, candidate, passNumber);
        latestRender = rendered;
        latestReview = null;
        passCount = passNumber;
        await writeSessionStatus(paths, { state: "awaiting_editorial_review", pass_number: passNumber, max_passes: MAX_EVALUATED_PASSES, candidate_hash: rendered.candidateHash, readiness: rendered.evaluation.readiness });
        process.stderr.write(`Candidate evaluated for pass ${passNumber}/${MAX_EVALUATED_PASSES}. Read candidate-preview.pdf and candidate-preview.json, then write editorial-review.json and create EDITORIAL_REVIEW.\n`);
      } catch (error) {
        await unlink(submitPath).catch(() => undefined);
        await writeSessionStatus(paths, { state: "candidate_or_preview_error", pass_number: passCount, error: error instanceof Error ? error.message : "validation failed" });
        process.stderr.write(`Candidate rejected locally or by preview: ${error instanceof Error ? error.message : "validation failed"}\n`);
        process.stderr.write(`Repair ${candidatePath}, then create ${RENDER_MARKER} to try again.\n`);
      }
      continue;
    }

    if (await exists(reviewMarkerPath)) {
      await unlink(reviewMarkerPath).catch(() => undefined);
      try {
        if (!latestRender) throw new Error("Evaluate a candidate before submitting its editorial review");
        const rawCandidate = JSON.parse(await readFile(candidatePath, "utf8"));
        validateCandidate(rawCandidate, context);
        const currentCandidate = materializeCandidate(rawCandidate);
        if (candidateInputHash(currentCandidate) !== latestRender.candidateInputHash) throw new Error("The candidate changed after evaluation; render the current candidate again before reviewing it");
        const rawReview = JSON.parse(await readFile(reviewFilePath, "utf8"));
        const review = validateEditorialReview(rawReview, { candidateHash: latestRender.candidateHash, passNumber: latestRender.passNumber, candidate: latestRender.candidate });
        if (hasEditorialBlockingFinding(review)) {
          editorialBlockedCandidateHashes.add(review.candidate_hash);
          latestReview = null;
          const message = "The editorial review contains a blocking finding; revise the candidate before submission";
          await writeEditorialReviewResult(paths, {
            valid: true,
            submission_allowed: false,
            review_version: EDITORIAL_REVIEW_VERSION,
            candidate_hash: review.candidate_hash,
            pass_number: review.pass_number,
            error: message,
            findings: review.findings,
          });
          await writeSessionStatus(paths, {
            state: "editorial_revision_required",
            pass_number: passCount,
            max_passes: MAX_EVALUATED_PASSES,
            candidate_hash: review.candidate_hash,
            readiness: latestRender.evaluation.readiness,
            error: message,
          });
          process.stderr.write(`${message}. Make a material candidate revision, then create RENDER.\n`);
          continue;
        }
        latestReview = review;
        const evaluation = latestRender.evaluation;
        await writeEditorialReviewResult(paths, { valid: true, review_version: EDITORIAL_REVIEW_VERSION, candidate_hash: review.candidate_hash, pass_number: review.pass_number, readiness: evaluation.readiness, blockers: evaluation.blockers ?? [], review_items: evaluation.review_items ?? [], recommendations: evaluation.recommendations ?? [], non_actionable_gaps: evaluation.non_actionable_gaps ?? [], inference_notes: evaluation.inference_notes ?? [], findings: review.findings });
        const attempt = { ...latestRender, evaluation, editorialReview: review };
        const previousAttempt = attempts.at(-1);
        if (previousAttempt && previousAttempt.candidateHash !== attempt.candidateHash) {
          unchangedActionRevisions = actionSignature(previousAttempt.evaluation) === actionSignature(attempt.evaluation) ? unchangedActionRevisions + 1 : 0;
          const previousBlockers = issueStateSignature(issueList(previousAttempt.evaluation, "blockers"));
          const currentBlockers = issueStateSignature(issueList(attempt.evaluation, "blockers"));
          unchangedBlockerRevisions = previousAttempt.evaluation.readiness?.status === "blocked"
            && attempt.evaluation.readiness?.status === "blocked"
            && currentBlockers.length > 0
            && JSON.stringify(previousBlockers) === JSON.stringify(currentBlockers)
            ? unchangedBlockerRevisions + 1
            : 0;
        }
        attempts.push(attempt);
        if (isBetterAttempt(attempt, bestAttempt)) {
          bestAttempt = attempt;
          await replaceProtectedJson(resolve(paths.output, "best-candidate.json"), bestAttempt.candidate);
          await replaceProtectedBinary(resolve(paths.output, "best-candidate-preview.pdf"), bestAttempt.pdfBase64);
          await replaceProtectedJson(resolve(paths.output, "best-candidate-preview.json"), bestAttempt.preview);
        }
        const repeatedCandidate = seenCandidateHashes.has(attempt.candidateHash);
        seenCandidateHashes.add(attempt.candidateHash);
        await replaceProtectedJson(resolve(paths.output, "evaluation-history.json"), attempts.map((item) => ({ candidate_hash: item.candidateHash, pass_number: item.passNumber, readiness: item.evaluation.readiness, improvements: item.evaluation.improvements, regressions: item.evaluation.regressions })));
        if (evaluation.readiness.status === "ready" || evaluation.readiness.status === "ready_with_review") {
          fallbackReady = false;
          stopReason = null;
          await writeSessionStatus(paths, { state: "ready_for_submission", pass_number: passCount, max_passes: MAX_EVALUATED_PASSES, candidate_hash: attempt.candidateHash, readiness: evaluation.readiness });
          process.stderr.write(`Server evaluation is ${evaluation.readiness.status}. Submit this exact reviewed candidate when ready, or render a material revision first.\n`);
        } else if (evaluation.readiness.status === "blocked") {
          const repeatedBlockers = unchangedBlockerRevisions >= 2;
          fallbackReady = (repeatedBlockers || passCount >= MAX_EVALUATED_PASSES)
            && isEligibleFallback(bestAttempt, editorialBlockedCandidateHashes);
          stopReason = repeatedBlockers ? "unchanged_blockers" : passCount >= MAX_EVALUATED_PASSES ? "max_passes" : null;
          await writeSessionStatus(paths, { state: fallbackReady ? "fallback_available" : "blocked", pass_number: passCount, max_passes: MAX_EVALUATED_PASSES, candidate_hash: attempt.candidateHash, readiness: evaluation.readiness, ...(stopReason ? { stop_reason: stopReason } : {}) });
          if (fallbackReady) process.stderr.write(`Server evaluation is blocked, but a reviewed non-blocked fallback is available (${stopReason}).\n`);
          else if (stopReason) {
            const terminalError = new Error(`Bounded tailoring loop stopped with unresolved blocking issues (${stopReason})`);
            terminalError.code = "TAILORING_TERMINAL";
            throw terminalError;
          }
          else process.stderr.write("Server evaluation is blocked. Resolve the concrete blocker before submitting.\n");
        } else {
          fallbackReady = passCount >= MAX_EVALUATED_PASSES || repeatedCandidate || unchangedActionRevisions >= 2;
          stopReason = repeatedCandidate ? "repeated_candidate" : unchangedActionRevisions >= 2 ? "unchanged_instrumentation" : passCount >= MAX_EVALUATED_PASSES ? "max_passes" : null;
          await writeSessionStatus(paths, { state: fallbackReady ? "fallback_available" : "revision_required", pass_number: passCount, max_passes: MAX_EVALUATED_PASSES, candidate_hash: attempt.candidateHash, readiness: evaluation.readiness, stop_reason: stopReason });
          process.stderr.write(fallbackReady ? `Bounded revision loop stopped (${stopReason}). SUBMIT may use the best reviewed non-blocked candidate.\n` : `Concrete server issues remain. Revise candidate.json and create RENDER for pass ${passCount + 1}/${MAX_EVALUATED_PASSES}.\n`);
        }
      } catch (error) {
        if (error?.code === "TAILORING_TERMINAL") throw error;
        const message = error instanceof Error ? error.message : "invalid editorial review";
        await writeEditorialReviewResult(paths, { valid: false, candidate_hash: latestRender?.candidateHash ?? null, pass_number: latestRender?.passNumber ?? passCount, error: message });
        await writeSessionStatus(paths, { state: "editorial_review_rejected", pass_number: latestRender?.passNumber ?? passCount, error: message });
        process.stderr.write(`Editorial review rejected: ${message}. Repair editorial-review.json and recreate EDITORIAL_REVIEW.\n`);
      }
      continue;
    }

    if (await exists(submitPath)) {
      try {
        const notes = await readReviewNotes(paths.output);
        const currentInferenceNotes = await readInferenceNotes(paths.output);
        let selectedAttempt = null;
        if (!fallbackReady && latestRender && latestReview) {
          const rawCandidate = JSON.parse(await readFile(candidatePath, "utf8"));
          validateCandidate(rawCandidate, context);
          const currentCandidate = materializeCandidate(rawCandidate);
          if (candidateInputHash(currentCandidate) === latestRender.candidateInputHash) selectedAttempt = { ...latestRender, editorialReview: latestReview };
        }
        // A normal ready submission must use the exact candidate currently
        // present in candidate.json.  Selecting a prior best attempt is only
        // a bounded-fallback behavior after the loop has explicitly stopped.
        if (!selectedAttempt && fallbackReady && isEligibleFallback(bestAttempt, editorialBlockedCandidateHashes)) selectedAttempt = bestAttempt;
        if (!selectedAttempt) throw new Error("No exact reviewed non-blocked candidate is available for submission");
        const readinessStatus = selectedAttempt.evaluation.readiness.status;
        const fallback = fallbackReady;
        if (readinessStatus === "revise" && !fallbackReady) throw new Error("The server still requests revision; reach the bounded fallback before submitting");
        if (readinessStatus === "blocked") throw new Error("Blocked candidates cannot be submitted");
        if (hasEditorialBlockingFinding(selectedAttempt.editorialReview)) throw new Error("Editorial review contains a blocking finding; revise the candidate before submitting");
        if (JSON.stringify(currentInferenceNotes) !== JSON.stringify(selectedAttempt.inferenceNotes ?? [])) throw new Error("inference-notes.json changed after the selected candidate was reviewed");
        const finalNotes = fallback ? await appendReviewNote(notes, fallbackReviewNote(selectedAttempt, passCount, stopReason)) : notes;
        await replaceProtectedJson(resolve(paths.output, "normalized-candidate.json"), selectedAttempt.candidate);
        return { candidate: selectedAttempt.candidate, candidateHash: selectedAttempt.candidateHash, reviewNotes: finalNotes, inferenceNotes: selectedAttempt.inferenceNotes ?? [], editorialReview: selectedAttempt.editorialReview, allowBoundedFallback: fallback };
      } catch (error) {
        await unlink(submitPath).catch(() => undefined);
        const message = error instanceof Error ? error.message : "submission is not ready";
        await writeSessionStatus(paths, { state: "submit_rejected", pass_number: passCount, error: message });
        process.stderr.write(`Submission rejected: ${message}\n`);
      }
      continue;
    }

    if (!(await exists(renderPath)) && !(await exists(reviewMarkerPath)) && !(await exists(submitPath))) await wait(750);
  }
  throw new Error("The tailoring session expired before a valid candidate was ready");
}

export async function runSession(sessionUrl, workspace, options = {}) {
  const origin = serverOriginFromSessionUrl(sessionUrl);
  const code = options.code === undefined ? await readCode() : validateCode(options.code);
  const exchange = await requestJson(`${origin}/api/v1/tailoring/exchange`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ protocol_version: PROTOCOL_VERSION, code }) });
  if (exchange.protocol_version !== PROTOCOL_VERSION || typeof exchange.capability !== "string") throw new Error("The server returned an incompatible tailoring protocol");
  const capability = exchange.capability;
  const context = await requestJson(`${origin}/api/v1/tailoring/context`, { headers: { "X-Aergia-Tailoring-Capability": capability } });
  if (context.protocol_version !== PROTOCOL_VERSION || context.evaluation_version !== "tailoring-evaluation-v1") throw new Error("The tailoring context is incompatible with this skill");
  const paths = await prepareWorkspace(workspace, context);
  if (context.rendered_source?.endpoint) {
    try {
      const sourcePreview = await requestJson(`${origin}${context.rendered_source.endpoint}`, { headers: { "X-Aergia-Tailoring-Capability": capability } });
      await writeProtectedBinary(resolve(paths.source, "source-cv.pdf"), sourcePreview.pdf_base64);
      await writeFile(resolve(paths.source, "source-cv-render.json"), `${JSON.stringify({ format: sourcePreview.format, page_count: sourcePreview.page_count, candidate_hash: sourcePreview.candidate_hash, scanner_result: sourcePreview.scanner_result ?? null, evaluation: sourcePreview.evaluation ?? null }, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
    } catch (error) {
      process.stderr.write(`Source PDF preview unavailable: ${error instanceof Error ? error.message : "render failed"}\n`);
    }
  }
  process.stdout.write(`Context ready in ${paths.source}\n`);
  process.stdout.write(`Write ${resolve(paths.output, "candidate.json")} and create RENDER. After each server evaluation, write editorial-review.json and create EDITORIAL_REVIEW. Submit only an exact reviewed candidate when it is ready, ready-with-review, or the bounded fallback allows it.\n`);
  const selected = await waitForCandidate(paths, context, origin, capability);
  const result = await requestJson(`${origin}/api/v1/tailoring/submit`, { method: "POST", headers: { "Content-Type": "application/json", "X-Aergia-Tailoring-Capability": capability }, body: JSON.stringify({ context_hash: context.context_hash, expected_candidate_hash: selected.candidateHash, candidate: selected.candidate, review_notes: selected.reviewNotes, inference_notes: selected.inferenceNotes, editorial_review: selected.editorialReview, allow_bounded_fallback: selected.allowBoundedFallback }) });
  if (result.candidate_hash !== selected.candidateHash || result.evaluation?.candidate_hash !== selected.candidateHash) throw new Error("The submitted draft hash did not match its rendered evaluation");
  await writeFile(resolve(paths.output, "result.json"), `${JSON.stringify(result, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  await writeSessionStatus(paths, { state: "submitted", draft_cv_id: result.draft_cv_id, candidate_hash: result.candidate_hash, readiness: result.evaluation?.readiness ?? null });
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
