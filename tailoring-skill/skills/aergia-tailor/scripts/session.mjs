#!/usr/bin/env node

import { createInterface } from "node:readline/promises";
import { access, chmod, mkdir, readdir, readFile, rm, unlink, writeFile } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { materializeCandidate, validateCandidate } from "./validate-candidate.mjs";
import {
  EDITORIAL_REVIEW_VERSION,
  validateEditorialReview,
} from "./validate-editorial-review.mjs";

export const PROTOCOL_VERSION = 8;
const SUBMIT_MARKER = "SUBMIT";
const RENDER_MARKER = "RENDER";
const EDITORIAL_REVIEW_MARKER = "EDITORIAL_REVIEW";
const SEMANTIC_REFRESH_TIMEOUT_MS = 90_000;

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

async function assertFreshStagedWorkspace(workspace) {
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
      else throw new Error("Staged tailoring requires an empty workspace so stale source or candidate files cannot leak into an early pass");
    }
  }
  await walk(workspace);
}

async function prepareIndexWorkspace(workspace) {
  await assertFreshStagedWorkspace(workspace);
  const extraction = resolve(workspace, "extraction");
  const evidence = resolve(workspace, "evidence");
  const output = resolve(workspace, "output");
  await Promise.all([extraction, evidence, output].map((path) => mkdir(path, { recursive: true, mode: 0o700 })));
  return { extraction, evidence, output, workspace };
}

async function prepareEvidenceWorkspace(paths, context) {
  const versions = context.evidence_versions ?? {};
  await Promise.all([
    writeProtectedJson(resolve(paths.evidence, "context.json"), context),
    writeProtectedJson(resolve(paths.evidence, "profile.json"), context.profile),
    writeProtectedJson(resolve(paths.evidence, "candidate-evidence.json"), context.candidate_evidence),
    writeProtectedJson(resolve(paths.evidence, "candidate-index.json"), context.candidate_index),
    writeProtectedJson(resolve(paths.evidence, "linked-cv.json"), context.previous_cv ?? null),
    writeProtectedJson(resolve(paths.evidence, "linked-cv-scan.json"), context.linked_cv_scan ?? null),
    writeProtectedJson(resolve(paths.evidence, "opportunities.json"), context.opportunities ?? []),
    writeProtectedJson(resolve(paths.evidence, "retrieved-sources.json"), context.retrieved_sources ?? []),
    writeProtectedJson(resolve(paths.evidence, "versions.json"), versions),
    writeProtectedJson(resolve(paths.evidence, "templates.json"), context.templates ?? []),
    writeProtectedJson(resolve(paths.evidence, "capabilities.json"), context.capabilities ?? {}),
    writeProtectedJson(resolve(paths.evidence, "effective-appearance.json"), context.effective_appearance ?? {}),
  ]);
}

export function validateSourcePropositions(value, expectedSourceId, expectedFingerprint) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("source proposition result must be an object");
  const allowedSourceKeys = new Set(["source_id", "source_fingerprint", "claims"]);
  if (value.source_id !== expectedSourceId || value.source_fingerprint !== expectedFingerprint
    || Object.keys(value).some((key) => !allowedSourceKeys.has(key))
    || !Array.isArray(value.claims) || value.claims.length > 80) {
    throw new Error("source proposition result does not match the active source or fingerprint");
  }
  const allowedClaimKeys = new Set(["statement", "support", "source_excerpt", "associated_concepts"]);
  const allowedConceptKeys = new Set(["kind", "value", "relation"]);
  const allowedConceptKinds = new Set(["technology", "method", "collaborator", "artifact", "domain", "outcome", "scope", "other"]);
  const allowedConceptRelations = new Set(["used", "deployed_with", "tested_with", "tested_across", "collaborated_with", "created", "documented", "within", "associated_with"]);
  for (const claim of value.claims) {
    if (!claim || typeof claim !== "object" || Array.isArray(claim)
      || Object.keys(claim).some((key) => !allowedClaimKeys.has(key))
      || typeof claim.statement !== "string" || !claim.statement.trim()
      || claim.statement.trim().split(/\s+/).length > 18
      || claim.support !== "explicit"
      || typeof claim.source_excerpt !== "string" || !claim.source_excerpt.trim() || claim.source_excerpt.length > 250
      || !Array.isArray(claim.associated_concepts ?? [])) {
      throw new Error("source proposition result contains an invalid proposition");
    }
    for (const concept of claim.associated_concepts ?? []) {
      if (!concept || typeof concept !== "object" || Array.isArray(concept)
        || Object.keys(concept).some((key) => !allowedConceptKeys.has(key))
        || !allowedConceptKinds.has(concept.kind)
        || typeof concept.value !== "string" || !concept.value.trim() || concept.value.length > 160
        || !allowedConceptRelations.has(concept.relation)) {
        throw new Error("source proposition result contains an invalid concept relation");
      }
    }
  }
  return { source_id: value.source_id, source_fingerprint: value.source_fingerprint, claims: value.claims };
}

const BATCH_PROPOSITIONS_FILE = "candidate-propositions-batch.json";

export function validateBatchPropositions(value, expectedSourceIds) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("candidate-propositions-batch.json must be an object");
  if (value.schema_version !== "candidate-proposition-batch-v2"
    || Object.keys(value).some((key) => !["schema_version", "results"].includes(key))
    || !Array.isArray(value.results) || value.results.length > 24) {
    throw new Error("candidate-propositions-batch.json has an invalid shape");
  }
  const expected = new Map(expectedSourceIds.map((source) => [source.source_id, source.source_fingerprint]));
  const occurrences = new Map();
  for (const raw of value.results) {
    if (typeof raw?.source_id === "string") occurrences.set(raw.source_id, (occurrences.get(raw.source_id) ?? 0) + 1);
  }
  const results = [];
  for (const raw of value.results) {
    const fingerprint = expected.get(raw?.source_id);
    if (typeof raw?.source_id !== "string" || !fingerprint || occurrences.get(raw.source_id) !== 1
      || raw.source_fingerprint !== fingerprint) continue;
    try {
      results.push(validateSourcePropositions(raw, raw.source_id, fingerprint));
    } catch {
      // A malformed source remains stale. Valid peers still reach the backend.
    }
  }
  return results;
}

async function removeStagedFile(path) {
  try {
    await unlink(path);
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
  if (await exists(path)) throw new Error("The isolated source extraction files could not be cleared");
}

async function waitForBatchPropositions(paths, sources, expiresAt) {
  const path = resolve(paths.output, BATCH_PROPOSITIONS_FILE);
  const deadline = Math.min(Date.now() + SEMANTIC_REFRESH_TIMEOUT_MS, Date.parse(expiresAt));
  while (Date.now() < deadline) {
    if (await exists(path)) {
      try {
        const value = JSON.parse(await readFile(path, "utf8"));
        return validateBatchPropositions(value, sources);
      } catch {
        return [];
      }
    }
    await wait(500);
  }
  return [];
}

async function clearWorkspaceContents(workspace) {
  const entries = await readdir(workspace, { withFileTypes: true });
  await Promise.all(entries.map((entry) => rm(resolve(workspace, entry.name), { recursive: true, force: true })));
}

async function exposeComposerWorkspace(paths, context) {
  await clearWorkspaceContents(paths.workspace);
  await Promise.all([paths.extraction, paths.evidence, paths.output].map((path) => mkdir(path, { recursive: true, mode: 0o700 })));
  await prepareEvidenceWorkspace(paths, context);
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

function wait(milliseconds) {
  return new Promise((accept) => setTimeout(accept, milliseconds));
}

function ensureEvaluation(evaluation, evaluationId, candidateHash) {
  if (!evaluation || typeof evaluation !== "object") throw new Error("The server preview did not return a tailoring evaluation");
  if (evaluation.version !== "tailoring-evaluation-v2") throw new Error("The server returned an incompatible tailoring evaluation");
  if (typeof evaluationId !== "string" || !/^[A-Za-z0-9_-]{16,128}$/.test(evaluationId)) throw new Error("The server returned an invalid evaluation ID");
  if (evaluation.candidate_hash !== candidateHash) throw new Error("The server evaluation is bound to a different candidate");
  return evaluation;
}

async function renderCandidate(paths, origin, capability, context, candidate) {
  const preview = await requestJson(`${origin}/api/v1/tailoring/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Aergia-Tailoring-Capability": capability },
    body: JSON.stringify({ context_hash: context.context_hash, candidate }),
  });
  const evaluation = ensureEvaluation(preview.evaluation, preview.evaluation_id, preview.candidate_hash);
  await replaceProtectedBinary(resolve(paths.output, "candidate-preview.pdf"), preview.pdf_base64);
  const details = {
    format: preview.format,
    page_count: preview.page_count,
    evaluation_id: preview.evaluation_id,
    candidate_hash: preview.candidate_hash,
    scanner_result: preview.scanner_result ?? null,
    evaluation,
    render_warnings: Array.isArray(preview.render_warnings) ? preview.render_warnings : [],
  };
  await replaceProtectedJson(resolve(paths.output, "candidate-preview.json"), details);
  const attemptDirectory = resolve(paths.output, "attempts", preview.evaluation_id);
  await mkdir(attemptDirectory, { recursive: true, mode: 0o700 });
  await writeProtectedJson(resolve(attemptDirectory, "candidate.json"), candidate);
  await writeProtectedJson(resolve(attemptDirectory, "candidate-preview.json"), details);
  await writeProtectedBinary(resolve(attemptDirectory, "candidate-preview.pdf"), preview.pdf_base64);
  return {
    candidate,
    candidateHash: preview.candidate_hash,
    evaluationId: preview.evaluation_id,
    pdfBase64: preview.pdf_base64,
    preview: details,
    evaluation,
    attemptDirectory,
  };
}

async function writeSessionStatus(paths, state) {
  await replaceProtectedJson(resolve(paths.output, "tailoring-status.json"), state);
}

async function writeEditorialReviewResult(paths, result) {
  await replaceProtectedJson(resolve(paths.output, "editorial-review-result.json"), result);
}

function statusForHttpError(error) {
  return Number.isInteger(error?.status) ? `HTTP ${error.status}` : "network error";
}

function isAccessFailure(error) {
  return [401, 403, 410].includes(error?.status)
    || /expired|revoked|capability is no longer active/i.test(error?.message ?? "");
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

async function waitForCandidate(paths, context, origin, capability, runtimeMetrics) {
  const submitPath = resolve(paths.output, SUBMIT_MARKER);
  const renderPath = resolve(paths.output, RENDER_MARKER);
  const reviewMarkerPath = resolve(paths.output, EDITORIAL_REVIEW_MARKER);
  const candidatePath = resolve(paths.output, "candidate.json");
  const reviewFilePath = resolve(paths.output, "editorial-review.json");
  const selectionPath = resolve(paths.output, "selection.json");
  const attempts = new Map();
  let previewCount = 0;

  await writeSessionStatus(paths, { state: "awaiting_candidate" });
  while (Date.now() < Date.parse(context.expires_at)) {
    if (await exists(renderPath)) {
      await unlink(renderPath).catch(() => undefined);
      try {
        const raw = JSON.parse(await readFile(candidatePath, "utf8"));
        validateCandidate(raw, context);
        const candidate = materializeCandidate(raw);
        await replaceProtectedJson(resolve(paths.output, "normalized-candidate.json"), candidate);
        const attempt = await renderCandidate(paths, origin, capability, context, candidate);
        attempts.set(attempt.evaluationId, attempt);
        previewCount += 1;
        runtimeMetrics.renders = previewCount;
        runtimeMetrics.revision_count = Math.max(0, previewCount - 1);
        await replaceProtectedJson(resolve(paths.output, "runtime-metrics.json"), runtimeMetrics);
        await writeSessionStatus(paths, {
          state: "awaiting_editorial_review",
          evaluation_id: attempt.evaluationId,
          candidate_hash: attempt.candidateHash,
        });
        process.stderr.write(`Candidate preview ${previewCount} is ready. Review candidate-preview.pdf and candidate-preview.json. Write editorial-review.json with this evaluation_id (${attempt.evaluationId}) and candidate_hash (${attempt.candidateHash}), then create EDITORIAL_REVIEW.\n`);
      } catch (error) {
        await writeSessionStatus(paths, { state: "candidate_or_preview_error", error: error instanceof Error ? error.message : "validation failed" });
        process.stderr.write(`Candidate rejected locally or by preview: ${error instanceof Error ? error.message : "validation failed"}. Repair candidate.json and create RENDER to try again.\n`);
      }
      continue;
    }

    if (await exists(reviewMarkerPath)) {
      await unlink(reviewMarkerPath).catch(() => undefined);
      try {
        const rawReview = JSON.parse(await readFile(reviewFilePath, "utf8"));
        const attempt = attempts.get(rawReview?.evaluation_id);
        if (!attempt) throw new Error("Editorial review evaluation_id does not name a preview in this session");
        const review = validateEditorialReview(rawReview, {
          evaluationId: attempt.evaluationId,
          candidateHash: attempt.candidateHash,
          candidate: attempt.candidate,
        });
        attempt.editorialReview = review;
        await replaceProtectedJson(resolve(attempt.attemptDirectory, "editorial-review.json"), review);
        const evaluation = attempt.evaluation;
        await writeEditorialReviewResult(paths, {
          valid: true,
          review_version: EDITORIAL_REVIEW_VERSION,
          evaluation_id: review.evaluation_id,
          candidate_hash: review.candidate_hash,
          risk_findings: evaluation.risk_findings ?? [],
          review_items: evaluation.review_items ?? [],
          recommendations: evaluation.recommendations ?? [],
          non_actionable_gaps: evaluation.non_actionable_gaps ?? [],
          findings: review.findings,
        });
        await replaceProtectedJson(resolve(paths.output, "evaluation-history.json"), [...attempts.values()]
          .filter((item) => item.editorialReview)
          .map((item) => ({
            evaluation_id: item.evaluationId,
            candidate_hash: item.candidateHash,
            improvements: item.evaluation.improvements,
            regressions: item.evaluation.regressions,
            risk_findings: item.evaluation.risk_findings ?? [],
          })));
        await writeSessionStatus(paths, {
          state: "awaiting_agent_decision",
          evaluation_id: attempt.evaluationId,
          candidate_hash: attempt.candidateHash,
        });
        process.stderr.write(`Editorial review saved for evaluation ${attempt.evaluationId}. Review any concerns, make another useful revision if warranted, or write selection.json with this evaluation_id and candidate_hash and create SUBMIT.\n`);
      } catch (error) {
        const message = error instanceof Error ? error.message : "invalid editorial review";
        await writeEditorialReviewResult(paths, { valid: false, error: message });
        await writeSessionStatus(paths, { state: "editorial_review_rejected", error: message });
        process.stderr.write(`Editorial review rejected: ${message}. Repair editorial-review.json and recreate EDITORIAL_REVIEW.\n`);
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
        if (!attempt || attempt.candidateHash !== selection.candidate_hash || !attempt.editorialReview) {
          throw new Error("selection.json must name a reviewed preview from this session with the matching candidate_hash");
        }
        const attemptDirectory = resolve(paths.output, "attempts", attempt.evaluationId);
        const frozenCandidate = materializeCandidate(JSON.parse(await readFile(resolve(attemptDirectory, "candidate.json"), "utf8")));
        const frozenPreview = JSON.parse(await readFile(resolve(attemptDirectory, "candidate-preview.json"), "utf8"));
        const frozenReviewInput = JSON.parse(await readFile(resolve(attemptDirectory, "editorial-review.json"), "utf8"));
        const frozenReview = validateEditorialReview(frozenReviewInput, {
          evaluationId: attempt.evaluationId,
          candidateHash: attempt.candidateHash,
          candidate: frozenCandidate,
        });
        if (frozenPreview.evaluation_id !== attempt.evaluationId
          || frozenPreview.candidate_hash !== attempt.candidateHash) {
          throw new Error("The frozen attempt no longer matches its preview and evaluation binding");
        }
        const reviewNotes = await readReviewNotes(paths.output);
        selectedAttempt = { ...attempt, candidate: frozenCandidate, editorialReview: frozenReview, reviewNotes };
        await replaceProtectedJson(resolve(paths.output, "normalized-candidate.json"), frozenCandidate);
      } catch (error) {
        const message = error instanceof Error ? error.message : "submission selection is invalid";
        await writeSessionStatus(paths, { state: "submit_rejected", error: message });
        process.stderr.write(`Submission selection rejected: ${message}\n`);
        continue;
      }

      const metrics = await exists(resolve(paths.output, "runtime-metrics.json"))
        ? JSON.parse(await readFile(resolve(paths.output, "runtime-metrics.json"), "utf8"))
        : runtimeMetrics;
      Object.assign(runtimeMetrics, metrics, {
        renders: previewCount,
        revision_count: Math.max(0, previewCount - 1),
      });
      const requestBody = {
        context_hash: context.context_hash,
        evaluation_id: selectedAttempt.evaluationId,
        expected_candidate_hash: selectedAttempt.candidateHash,
        candidate: selectedAttempt.candidate,
        review_notes: selectedAttempt.reviewNotes,
        editorial_review: selectedAttempt.editorialReview,
        runtime_metrics: runtimeMetrics,
      };
      try {
        const result = await submitWithBackoff(`${origin}/api/v1/tailoring/submit`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Aergia-Tailoring-Capability": capability },
          body: JSON.stringify(requestBody),
        }, context.expires_at);
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
        const transient = error?.status === 429 || error?.status >= 500 || error?.status === undefined;
        await writeSessionStatus(paths, {
          state: transient ? "submit_recoverable_error" : "submit_rejected",
          evaluation_id: selectedAttempt.evaluationId,
          candidate_hash: selectedAttempt.candidateHash,
          error: `${statusForHttpError(error)}: ${message}`,
        });
        process.stderr.write(`Submit ${statusForHttpError(error)}: ${message}. Correct selection.json or the selected attempt's review/request inputs if needed, then recreate SUBMIT to retry.\n`);
      }
      continue;
    }

    await wait(750);
  }
  await writeSessionStatus(paths, { state: "session_expired", error: "The tailoring session expired before submission completed" });
  throw new Error("The tailoring session expired before submission completed");
}

export async function runSession(sessionUrl, workspace, options = {}) {
  const origin = serverOriginFromSessionUrl(sessionUrl);
  const code = options.code === undefined ? await readCode() : validateCode(options.code);
  const exchange = await requestJson(`${origin}/api/v1/tailoring/exchange`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ protocol_version: PROTOCOL_VERSION, code }) });
  if (exchange.protocol_version !== PROTOCOL_VERSION || typeof exchange.capability !== "string") throw new Error("The server returned an incompatible tailoring protocol");
  const capability = exchange.capability;
  const headers = { "X-Aergia-Tailoring-Capability": capability };
  const paths = await prepareIndexWorkspace(workspace);
  const runtimeMetrics = {
    candidate_cue_calls: 0,
    semantic_indexing_calls: 0,
    indexing_workers: 0,
    semantic_refresh_duration_ms: 0,
    semantic_batches_processed: 0,
    main_writer_calls: 1,
    renders: 0,
    revision_count: 0,
  };

  // Candidate indexing is checked before the job context is fetched. The
  // refresh worker sees only this source batch and its schema.
  let indexState = null;
  try {
    indexState = await requestJson(`${origin}/api/v1/tailoring/context/index-refresh`, { headers });
    if (indexState.protocol_version !== PROTOCOL_VERSION || indexState.stage !== "candidate_index_refresh"
      || !Array.isArray(indexState.sources)) throw new Error("The server returned an incompatible candidate index state");
  } catch (error) {
    process.stderr.write(`Candidate semantic refresh unavailable; continuing with deterministic Library sources: ${error instanceof Error ? error.message : "refresh state unavailable"}\n`);
  }

  if (indexState) {
    runtimeMetrics.candidate_cache_state = indexState.cache_state;
    runtimeMetrics.fresh_source_count = indexState.source_counts?.fresh ?? 0;
    runtimeMetrics.stale_source_count = indexState.source_counts?.stale ?? 0;
    runtimeMetrics.missing_source_count = indexState.source_counts?.missing ?? 0;
    if (indexState.sources.length > 0) {
      const refreshStartedAt = Date.now();
      const batchPath = resolve(paths.extraction, "source-batch.json");
      const batchOutputPath = resolve(paths.output, BATCH_PROPOSITIONS_FILE);
      await writeProtectedJson(batchPath, {
        schema_version: "candidate-source-batch-v1",
        semantic_contract: indexState.semantic_contract,
        sources: indexState.sources,
      });
      process.stdout.write(`Job-blind semantic refresh batch ready at ${batchPath}. Start ONE isolated worker with no inherited job/application context. Give it only this batch, candidate-source-batch.schema.json, candidate-proposition-batch.schema.json, and ${batchOutputPath}. The worker must keep each source independent. Do not provide a job, strategy, linked CV, scan, or tailoring conversation.\n`);
      const sourceResults = await waitForBatchPropositions(paths, indexState.sources, indexState.expires_at);
      runtimeMetrics.semantic_refresh_duration_ms = Date.now() - refreshStartedAt;
      runtimeMetrics.semantic_batches_processed = 1;
      runtimeMetrics.semantic_indexing_calls = sourceResults.length;
      runtimeMetrics.indexing_workers = 1;
      if (sourceResults.length) {
        try {
          const refreshResult = await requestJson(`${origin}/api/v1/tailoring/context/index-refresh`, {
            method: "POST",
            headers: { ...headers, "Content-Type": "application/json" },
            body: JSON.stringify({ source_results: sourceResults }),
          });
          runtimeMetrics.accepted_semantic_sources = refreshResult.accepted_source_ids?.length ?? 0;
          runtimeMetrics.rejected_semantic_sources = refreshResult.rejected_source_ids?.length ?? 0;
          runtimeMetrics.source_counts_after_refresh = refreshResult.source_counts ?? {};
        } catch (error) {
          process.stderr.write(`Semantic refresh result was not persisted; continuing with deterministic data: ${error instanceof Error ? error.message : "refresh write failed"}\n`);
        }
      } else {
        process.stderr.write("No valid semantic source results arrived within the refresh budget; continuing with deterministic data and current Library narratives.\n");
      }
      await Promise.all([removeStagedFile(batchPath), removeStagedFile(batchOutputPath)]);
    }
  }

  let context;
  try {
    context = await requestJson(`${origin}/api/v1/tailoring/context`, { headers });
  } catch (error) {
    // Semantic enrichment is optional, but the deterministic composition
    // context itself remains required to create a safe draft.
    throw error;
  }
  if (context.protocol_version !== PROTOCOL_VERSION || context.evaluation_version !== "tailoring-evaluation-v2") throw new Error("The server returned an incompatible protocol v8 tailoring context");
  runtimeMetrics.fresh_source_count = context.candidate_index?.semantic_source_counts?.fresh ?? runtimeMetrics.fresh_source_count ?? 0;
  runtimeMetrics.stale_source_count = context.candidate_index?.semantic_source_counts?.stale ?? runtimeMetrics.stale_source_count ?? 0;
  runtimeMetrics.missing_source_count = context.candidate_index?.semantic_source_counts?.missing ?? runtimeMetrics.missing_source_count ?? 0;
  runtimeMetrics.sources_retrieved = context.retrieved_sources?.length ?? 0;
  runtimeMetrics.writer_context_characters = context.writer_context_characters ?? 0;
  await exposeComposerWorkspace(paths, context);
  await replaceProtectedJson(resolve(paths.output, "runtime-metrics.json"), runtimeMetrics);
  process.stdout.write(`Complete job-aware composition context ready in ${paths.evidence}. Candidate cache: ${runtimeMetrics.fresh_source_count} fresh, ${runtimeMetrics.stale_source_count} stale, ${runtimeMetrics.missing_source_count} missing. Retrieve only this bounded source set, write one complete candidate to ${resolve(paths.output, "candidate.json")}, then create RENDER.\n`);

  if (context.rendered_source?.endpoint) {
    try {
      const sourcePreview = await requestJson(`${origin}${context.rendered_source.endpoint}`, { headers });
      await writeProtectedBinary(resolve(paths.evidence, "linked-cv.pdf"), sourcePreview.pdf_base64);
      await writeFile(resolve(paths.evidence, "linked-cv-render.json"), `${JSON.stringify({ format: sourcePreview.format, page_count: sourcePreview.page_count, candidate_hash: sourcePreview.candidate_hash, scanner_result: sourcePreview.scanner_result ?? null, evaluation: sourcePreview.evaluation ?? null }, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
    } catch (error) {
      process.stderr.write(`Linked CV PDF preview unavailable: ${error instanceof Error ? error.message : "render failed"}\n`);
    }
  }
  return waitForCandidate(paths, context, origin, capability, runtimeMetrics);
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
