#!/usr/bin/env node

import { createInterface } from "node:readline/promises";
import { createHash } from "node:crypto";
import { access, chmod, mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { materializeCandidate, validateCandidate } from "./validate-candidate.mjs";
import { evaluateCritique, MAX_CRITIQUE_PASSES } from "./validate-critique.mjs";

export const PROTOCOL_VERSION = 4;
const SUBMIT_MARKER = "SUBMIT";
const RENDER_MARKER = "RENDER";
const CRITIQUE_MARKER = "CRITIQUE";

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

async function renderCandidate(paths, origin, capability, context, candidate, passNumber) {
  const candidateInputDigest = candidateInputHash(candidate);
  const preview = await requestJson(`${origin}/api/v1/tailoring/preview`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Aergia-Tailoring-Capability": capability,
    },
    body: JSON.stringify({ context_hash: context.context_hash, candidate }),
  });
  await replaceProtectedBinary(resolve(paths.output, "candidate-preview.pdf"), preview.pdf_base64);
  const details = {
    format: preview.format,
    page_count: preview.page_count,
    candidate_hash: preview.candidate_hash,
    candidate_input_hash: candidateInputDigest,
    pass_number: passNumber,
    scanner_result: preview.scanner_result ?? null,
    render_warnings: Array.isArray(preview.render_warnings) ? preview.render_warnings : [],
  };
  await replaceProtectedJson(resolve(paths.output, "candidate-preview.json"), details);
  return {
    candidate,
    candidateInputHash: candidateInputDigest,
    candidateHash: preview.candidate_hash,
    passNumber,
    pdfBase64: preview.pdf_base64,
    preview: details,
  };
}

async function writeSessionStatus(paths, state) {
  await replaceProtectedJson(resolve(paths.output, "critique-status.json"), state);
}

async function writeCritiqueResult(paths, result) {
  await replaceProtectedJson(resolve(paths.output, "critique-result.json"), result);
}

async function appendReviewNote(notes, note) {
  const boundedNote = note.slice(0, 1_000);
  return [...notes.slice(0, 19), boundedNote];
}

function isBetterAttempt(current, best) {
  if (!best) return true;
  if (current.evaluation.passed !== best.evaluation.passed) return current.evaluation.passed;
  if (current.evaluation.score !== best.evaluation.score) return current.evaluation.score > best.evaluation.score;
  if (current.evaluation.critical_count !== best.evaluation.critical_count) {
    return current.evaluation.critical_count < best.evaluation.critical_count;
  }
  return current.evaluation.finding_count < best.evaluation.finding_count;
}

function fallbackReviewNote(best, passCount, stopReason) {
  const unresolved = [
    ...best.evaluation.findings
      .filter((finding) => finding.severity === "critical" || finding.severity === "important")
      .map((finding) => finding.severity + ": " + finding.problem),
    ...best.evaluation.requirement_review
      .filter((review) => review.status === "supported_but_missing")
      .map((review) => review.rationale),
  ];
  const reason = stopReason === "repeated_candidate" ? "the writer repeated a previously critiqued candidate" :
    stopReason === "stalled" ? "two revisions produced less than two points of improvement" :
      "the five-pass limit was reached";
  const remaining = unresolved.length > 0 ? unresolved.join("; ") : "the readiness score remained below threshold";
  return (`Critique gate not passed after ${passCount} critique pass(es): best candidate scored ${best.evaluation.score}/100 (threshold ${best.evaluation.threshold}); ${reason}. Please review remaining findings: ${remaining}`).slice(0, 1_000);
}

async function waitForCandidate(paths, context, origin, capability) {
  const submitPath = resolve(paths.output, SUBMIT_MARKER);
  const renderPath = resolve(paths.output, RENDER_MARKER);
  const critiquePath = resolve(paths.output, CRITIQUE_MARKER);
  const candidatePath = resolve(paths.output, "candidate.json");
  const critiqueFilePath = resolve(paths.output, "critique.json");
  const requirements = Array.isArray(context.scanner?.requirement_extraction?.requirements)
    ? context.scanner.requirement_extraction.requirements
    : (Array.isArray(context.requirements) ? context.requirements : []);
  const critiqueHistory = [];
  const seenCandidateHashes = new Set();
  const scores = [];
  let latestRender = null;
  let latestEvaluation = null;
  let bestAttempt = null;
  let passCount = 0;
  let fallbackReady = false;
  let stopReason = null;

  await writeSessionStatus(paths, { state: "awaiting_candidate", pass_number: 0, max_passes: MAX_CRITIQUE_PASSES });
  while (Date.now() < Date.parse(context.expires_at)) {
    if (await exists(renderPath)) {
      await unlink(renderPath).catch(() => undefined);
      if (fallbackReady && (stopReason === "repeated_candidate" || stopReason === "stalled")) {
        await writeSessionStatus(paths, {
          state: "fallback_available",
          pass_number: passCount,
          max_passes: MAX_CRITIQUE_PASSES,
          best_score: bestAttempt?.evaluation.score ?? null,
          stop_reason: stopReason,
        });
        process.stderr.write(`Critique has stopped (${stopReason}). SUBMIT will use the best reviewed candidate.\n`);
        continue;
      }
      if (passCount >= MAX_CRITIQUE_PASSES) {
        fallbackReady = Boolean(bestAttempt);
        stopReason = "max_passes";
        await writeSessionStatus(paths, {
          state: fallbackReady ? "fallback_available" : "best_candidate_passed",
          pass_number: passCount,
          max_passes: MAX_CRITIQUE_PASSES,
          best_score: bestAttempt?.evaluation.score ?? null,
        });
        process.stderr.write("The five-critique-pass limit has been reached. Inspect best-candidate.json; the helper will allow a fallback submit of that reviewed candidate.\n");
        continue;
      }
      await unlink(critiquePath).catch(() => undefined);
      await unlink(critiqueFilePath).catch(() => undefined);
      await unlink(resolve(paths.output, "critique-result.json")).catch(() => undefined);
      try {
        const raw = JSON.parse(await readFile(candidatePath, "utf8"));
        validateCandidate(raw, context);
        const candidate = materializeCandidate(raw);
        await replaceProtectedJson(resolve(paths.output, "normalized-candidate.json"), candidate);
        const passNumber = passCount + 1;
        const rendered = await renderCandidate(paths, origin, capability, context, candidate, passNumber);
        latestRender = rendered;
        latestEvaluation = null;
        passCount = passNumber;
        await writeSessionStatus(paths, {
          state: "awaiting_critique",
          pass_number: passNumber,
          max_passes: MAX_CRITIQUE_PASSES,
          candidate_hash: rendered.candidateHash,
        });
        process.stderr.write(`Candidate rendered for critique pass ${passNumber}/${MAX_CRITIQUE_PASSES}. Read candidate-preview.pdf and candidate-preview.json, then write critique.json and create CRITIQUE.\n`);
      } catch (error) {
        await unlink(submitPath).catch(() => undefined);
        await writeSessionStatus(paths, { state: "candidate_or_preview_error", pass_number: passCount, error: error instanceof Error ? error.message : "validation failed" });
        process.stderr.write(`Candidate rejected locally or by preview: ${error instanceof Error ? error.message : "validation failed"}\n`);
        process.stderr.write(`Repair ${candidatePath}, then create ${renderPath} to try again.\n`);
      }
      continue;
    }

    if (await exists(critiquePath)) {
      await unlink(critiquePath).catch(() => undefined);
      try {
        if (!latestRender) throw new Error("Render a candidate before submitting its critique");
        const rawCandidate = JSON.parse(await readFile(candidatePath, "utf8"));
        validateCandidate(rawCandidate, context);
        const currentCandidate = materializeCandidate(rawCandidate);
        if (candidateInputHash(currentCandidate) !== latestRender.candidateInputHash) {
          throw new Error("The candidate changed after rendering; render the current candidate again before critiquing it");
        }
        const rawCritique = JSON.parse(await readFile(critiqueFilePath, "utf8"));
        const evaluation = evaluateCritique(rawCritique, {
          candidateHash: latestRender.candidateHash,
          passNumber: latestRender.passNumber,
          candidate: latestRender.candidate,
          requirements,
        });
        latestEvaluation = evaluation;
        const result = {
          valid: true,
          rubric_version: evaluation.rubric_version,
          candidate_hash: evaluation.candidate_hash,
          pass_number: evaluation.pass_number,
          score: evaluation.score,
          threshold: evaluation.threshold,
          passed: evaluation.passed,
          critical_count: evaluation.critical_count,
          required_evidence_gaps: evaluation.required_evidence_gaps,
          total_deduction: evaluation.total_deduction,
          category_scores: evaluation.category_scores,
          finding_count: evaluation.finding_count,
          unsupported_requirement_count: evaluation.unsupported_requirement_count,
          findings: evaluation.findings,
          requirement_review: evaluation.requirement_review,
        };
        await writeCritiqueResult(paths, result);
        const attempt = { ...latestRender, evaluation };
        if (isBetterAttempt(attempt, bestAttempt)) {
          bestAttempt = attempt;
          await replaceProtectedJson(resolve(paths.output, "best-candidate.json"), bestAttempt.candidate);
          await replaceProtectedBinary(resolve(paths.output, "best-candidate-preview.pdf"), bestAttempt.pdfBase64);
          await replaceProtectedJson(resolve(paths.output, "best-candidate-preview.json"), {
            ...bestAttempt.preview,
            critique_score: evaluation.score,
            critique_passed: evaluation.passed,
          });
        }
        const repeatedCandidate = seenCandidateHashes.has(latestRender.candidateInputHash);
        seenCandidateHashes.add(latestRender.candidateInputHash);
        scores.push(evaluation.score);
        const stalled = scores.length >= 3 &&
          scores[scores.length - 1] - scores[scores.length - 2] < 2 &&
          scores[scores.length - 2] - scores[scores.length - 3] < 2;
        critiqueHistory.push(result);
        await replaceProtectedJson(resolve(paths.output, "critique-history.json"), critiqueHistory);

        if (evaluation.passed) {
          fallbackReady = false;
          stopReason = null;
          await writeSessionStatus(paths, {
            state: "passed",
            pass_number: passCount,
            max_passes: MAX_CRITIQUE_PASSES,
            score: evaluation.score,
            candidate_hash: evaluation.candidate_hash,
          });
          process.stderr.write(`Critique passed at ${evaluation.score}/100. Submit this unchanged rendered candidate, or revise and render again before submitting.\n`);
        } else {
          fallbackReady = passCount >= MAX_CRITIQUE_PASSES || repeatedCandidate || stalled;
          stopReason = repeatedCandidate ? "repeated_candidate" : stalled ? "stalled" : passCount >= MAX_CRITIQUE_PASSES ? "max_passes" : null;
          await writeSessionStatus(paths, {
            state: fallbackReady ? "fallback_available" : "revision_required",
            pass_number: passCount,
            max_passes: MAX_CRITIQUE_PASSES,
            score: evaluation.score,
            threshold: evaluation.threshold,
            passed: false,
            critical_count: evaluation.critical_count,
            best_score: bestAttempt?.evaluation.score ?? null,
            stop_reason: stopReason,
          });
          const detail = fallbackReady
            ? `Critique stopped (${stopReason}). Inspect best-candidate.json; SUBMIT will use that reviewed candidate and attach a note for the user.`
            : `Critique score ${evaluation.score}/100; ${evaluation.critical_count} Critical issue(s). Revise candidate.json and create RENDER for pass ${passCount + 1}/${MAX_CRITIQUE_PASSES}.`;
          process.stderr.write(detail + "\n");
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : "invalid critique";
        await writeCritiqueResult(paths, {
          valid: false,
          pass_number: latestRender?.passNumber ?? passCount,
          candidate_hash: latestRender?.candidateHash ?? null,
          error: message,
        });
        await writeSessionStatus(paths, {
          state: "critique_rejected",
          pass_number: latestRender?.passNumber ?? passCount,
          error: message,
        });
        process.stderr.write(`Critique rejected: ${message}. Repair critique.json and recreate CRITIQUE, or render the updated candidate.\n`);
      }
      continue;
    }

    if (await exists(submitPath)) {
      try {
        const notes = await readReviewNotes(paths.output);
        let selectedAttempt = null;
        let fallbackNote = null;
        if (latestRender && latestEvaluation?.passed) {
          const rawCandidate = JSON.parse(await readFile(candidatePath, "utf8"));
          validateCandidate(rawCandidate, context);
          const currentCandidate = materializeCandidate(rawCandidate);
          if (candidateInputHash(currentCandidate) === latestRender.candidateInputHash) {
            selectedAttempt = { ...latestRender, evaluation: latestEvaluation };
          }
        }
        if (!selectedAttempt && bestAttempt?.evaluation.passed) {
          const rawCandidate = JSON.parse(await readFile(candidatePath, "utf8"));
          validateCandidate(rawCandidate, context);
          const currentCandidate = materializeCandidate(rawCandidate);
          if (candidateInputHash(currentCandidate) === bestAttempt.candidateInputHash) selectedAttempt = bestAttempt;
        }
        if (!selectedAttempt && fallbackReady && bestAttempt) {
          selectedAttempt = bestAttempt;
          if (!bestAttempt.evaluation.passed) fallbackNote = fallbackReviewNote(bestAttempt, passCount, stopReason);
        }
        if (!selectedAttempt) {
          throw new Error("No passing critique is bound to the current candidate. Render and critique it before SUBMIT; after the limit, SUBMIT uses best-candidate.json.");
        }
        const finalNotes = fallbackNote ? await appendReviewNote(notes, fallbackNote) : notes;
        await replaceProtectedJson(resolve(paths.output, "normalized-candidate.json"), selectedAttempt.candidate);
        return {
          candidate: selectedAttempt.candidate,
          candidateHash: selectedAttempt.candidateHash,
          reviewNotes: finalNotes,
        };
      } catch (error) {
        await unlink(submitPath).catch(() => undefined);
        const message = error instanceof Error ? error.message : "submission is not ready";
        await writeSessionStatus(paths, { state: "submit_rejected", pass_number: passCount, error: message });
        process.stderr.write(`Submission rejected: ${message}\n`);
      }
      continue;
    }

    if (!(await exists(renderPath)) && !(await exists(critiquePath)) && !(await exists(submitPath))) {
      await wait(750);
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
        `${JSON.stringify({ format: sourcePreview.format, page_count: sourcePreview.page_count, candidate_hash: sourcePreview.candidate_hash, scanner_result: sourcePreview.scanner_result ?? null }, null, 2)}\n`,
        { encoding: "utf8", mode: 0o600 },
      );
    } catch (error) {
      process.stderr.write(`Source PDF preview unavailable: ${error instanceof Error ? error.message : "render failed"}\n`);
    }
  }
  process.stdout.write(`Context ready in ${paths.source}\n`);
  process.stdout.write(`Write ${resolve(paths.output, "candidate.json")} and create RENDER. After each preview, write critique.json and create CRITIQUE. Submit only after critique passes, or use the reviewed best candidate after the bounded fallback is available.\n`);
  const { candidate, candidateHash, reviewNotes } = await waitForCandidate(paths, context, origin, capability);
  const result = await requestJson(`${origin}/api/v1/tailoring/submit`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Aergia-Tailoring-Capability": capability,
    },
    body: JSON.stringify({
      context_hash: context.context_hash,
      expected_candidate_hash: candidateHash,
      candidate,
      review_notes: reviewNotes,
    }),
  });
  if (result.candidate_hash !== candidateHash) {
    throw new Error("The submitted draft hash did not match its rendered critique");
  }
  await writeFile(resolve(paths.output, "result.json"), `${JSON.stringify(result, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  await writeSessionStatus(paths, { state: "submitted", draft_cv_id: result.draft_cv_id, candidate_hash: result.candidate_hash });
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
