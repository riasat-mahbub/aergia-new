import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, readFile, readdir, rename, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  PROTOCOL_VERSION,
  runSession,
  serverOriginFromSessionUrl,
} from "../skills/aergia-tailor/scripts/session.mjs";

const sha = (value) => createHash("sha256").update(JSON.stringify(value)).digest("hex");
const sleep = (duration = 25) => new Promise((resolve) => setTimeout(resolve, duration));
const capability = "capability-secret-do-not-write";
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

async function waitForJson(path, predicate, timeoutMs = 8_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const value = JSON.parse(await readFile(path, "utf8"));
      if (predicate(value)) return value;
    } catch {
      // The helper may still be creating or replacing the file.
    }
    await sleep();
  }
  throw new Error(`Timed out waiting for ${path}`);
}

async function allWorkspaceText(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const contents = [];
  for (const entry of entries) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) contents.push(await allWorkspaceText(path));
    else contents.push(await readFile(path, "utf8"));
  }
  return contents.join("\n");
}

async function writeIdealTargetAtomically(output, contents = "# Ideal target\n\nA fictional CV for the target role.\n") {
  const temporaryPath = join(output, ".ideal-target.md.tmp");
  const targetPath = join(output, "ideal-target.md");
  await writeFile(temporaryPath, contents);
  await rename(temporaryPath, targetPath);
  return targetPath;
}

function fitReviewFor(preview, status = "completed") {
  const binding = {
    version: "fit-review-v1",
    evaluation_id: preview.evaluation_id,
    candidate_hash: preview.candidate_hash,
    pdf_sha256: preview.pdf_sha256,
  };
  if (status === "completed") {
    return {
      ...binding,
      status,
      mode: "fresh_agent",
      verdict: "generic",
      rationale: "The PDF shows relevant tools but does not connect examples to the role's main responsibilities.",
      strong_connections: ["Visible Python API work"],
      weak_or_missing_connections: ["Production support ownership"],
      recommended_changes: ["Connect the API example to a stated responsibility."],
    };
  }
  return { ...binding, status, reason: "A fresh reviewer who could inspect the PDF was unavailable." };
}

async function releaseIdealTarget(evidence, output) {
  const jobPath = join(evidence, "job.json");
  const contextPath = join(evidence, "context.json");
  const job = await waitForJson(jobPath, (value) => value.company === "Example");
  await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "awaiting_ideal_target");
  assert.deepEqual((await readdir(evidence)).sort(), ["job.json"]);
  await assert.rejects(readFile(contextPath, "utf8"), { code: "ENOENT" });
  await writeIdealTargetAtomically(output);
  await waitForJson(contextPath, (value) => value.protocol_version === PROTOCOL_VERSION);
  return job;
}

function makeContext() {
  return {
    protocol_version: PROTOCOL_VERSION,
    evaluation_version: "tailoring-evaluation-v2",
    session_id: "session-1",
    application_id: "application-1",
    source_cv_id: null,
    expires_at: new Date(Date.now() + 60_000).toISOString(),
    context_hash: "a".repeat(64),
    job: { company: "Example", role: "Engineer", job_url: null, description: "Build APIs", user_instructions: "Emphasize backend delivery" },
    dossier: "PROFILE\nAda Lovelace\n\nLIBRARY HISTORY\nBuilt Python APIs and deployment workflows.",
    templates: [{ id: "generic-minimal", manifest: {} }],
    selected_template_id: "generic-minimal",
    selected_template_manifest: {},
    capabilities: { section_types: ["profile", "experience", "projects"] },
    capabilities_hash: "b".repeat(64),
    effective_appearance: {},
  };
}

function textFromCandidate(candidate) {
  const sectionText = candidate?.sections?.find((section) => section.type === "profile")?.data?.summary?.[0]?.items?.[0]?.text;
  return candidate?.raw_content ?? sectionText ?? "Candidate summary";
}

function canonicalCandidate(candidate) {
  return {
    id: "server-candidate-id",
    title: candidate.title ?? "Tailored candidate",
    template_id: "generic-minimal",
    sections: [{
      id: "profile",
      type: "profile",
      title: "Profile",
      enabled: true,
      data: {
        name: "Ada Lovelace",
        summary: [{
          id: "rtb_server_stable_01",
          type: "paragraph",
          items: [{ id: "rti_server_stable_01", text: textFromCandidate(candidate) }],
        }],
      },
    }],
    customizations: {},
  };
}

function withPreviewReservationRoutes(handler, onReservationRequest = () => undefined) {
  return async (url, options = {}) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/preview-reservations")) {
      const body = JSON.parse(options.body);
      onReservationRequest(path, options);
      return Response.json({
        reservation_id: body.request_id,
        candidate_hash: sha(canonicalCandidate(body.candidate)),
        expires_at: new Date(Date.now() + 60_000).toISOString(),
      });
    }
    if (/\/preview-reservations\/[0-9a-f-]+\/release$/.test(path)) {
      onReservationRequest(path, options);
      return Response.json({ status: "released" });
    }
    return handler(url, options);
  };
}

async function runComposerSession({
  previewCount = 1,
  selectedPreviewIndex = previewCount - 1,
  firstSubmitStatus = null,
  loseFirstSubmitResponse = false,
  reviewNotes = null,
  wrongSelectionFirst = false,
  reviewPreviewIndices = [],
  reviewStatus = "completed",
  sameCandidateAcrossPreviews = false,
} = {}) {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-v9-"));
  const output = join(workspace, "output");
  const evidence = join(workspace, "evidence");
  const context = makeContext();
  const calls = [];
  const previewBodies = [];
  const submitBodies = [];
  const helperOutput = [];
  const originalStdoutWrite = process.stdout.write;
  const originalStderrWrite = process.stderr.write;
  let submitCount = 0;
  let savedSubmitResult = null;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options = {}) => {
    const path = new URL(String(url)).pathname;
    calls.push({ path, options });
    if (path.endsWith("/exchange")) {
      assert.deepEqual(JSON.parse(options.body), {
        protocol_version: PROTOCOL_VERSION,
        session_id: "session-1",
        code: "code-1234567890123456",
      });
      return Response.json({ protocol_version: PROTOCOL_VERSION, session_id: "session-1", capability });
    }
    if (path.endsWith("/context")) return Response.json(context);
    if (path.endsWith("/preview-reservations")) {
      const body = JSON.parse(options.body);
      assert.equal(body.context_hash, context.context_hash);
      assert.ok(UUID_PATTERN.test(body.request_id));
      return Response.json({
        reservation_id: body.request_id,
        candidate_hash: sha(canonicalCandidate(body.candidate)),
        expires_at: new Date(Date.now() + 60_000).toISOString(),
      });
    }
    if (/\/preview-reservations\/[0-9a-f-]+\/release$/.test(path)) {
      return Response.json({ status: "released" });
    }
    if (path.endsWith("/preview")) {
      const body = JSON.parse(options.body);
      previewBodies.push(body);
      assert.ok(UUID_PATTERN.test(body.reservation_id));
      const candidate = canonicalCandidate(body.candidate);
      const hash = sha(candidate);
      const evaluationId = `evaluation_${String(previewBodies.length).padStart(20, "0")}`;
      const pdfBytes = Buffer.from(`pdf-${previewBodies.length}`);
      return Response.json({
        protocol_version: PROTOCOL_VERSION,
        candidate,
        format: "pdf",
        pdf_base64: pdfBytes.toString("base64"),
        pdf_sha256: createHash("sha256").update(pdfBytes).digest("hex"),
        page_count: 1,
        evaluation_id: evaluationId,
        candidate_hash: hash,
        scanner_result: { job_fit: { status: "review" }, findings: [] },
        evaluation: {
          version: "tailoring-evaluation-v2",
          candidate_hash: hash,
          risk_findings: [],
          review_items: [],
          recommendations: [],
        },
        render_warnings: [],
      });
    }
    if (path.endsWith("/submit")) {
      const body = JSON.parse(options.body);
      submitBodies.push(body);
      submitCount += 1;
      if (firstSubmitStatus && submitCount === 1) {
        return Response.json({ detail: "temporary request issue; retry the selected attempt" }, { status: firstSubmitStatus });
      }
      savedSubmitResult = savedSubmitResult ?? {
        protocol_version: PROTOCOL_VERSION,
        status: "draft_ready",
        draft_cv_id: "draft-1",
        evaluation_id: body.evaluation_id,
        candidate_hash: body.candidate_hash,
        candidate: body.candidate,
        evaluation: {
          version: "tailoring-evaluation-v2",
          candidate_hash: body.candidate_hash,
        },
      };
      if (loseFirstSubmitResponse && submitCount === 1) throw new Error("connection reset after the server saved the draft");
      return Response.json(savedSubmitResult);
    }
    throw new Error(`Unexpected request ${path}`);
  };
  process.stdout.write = function (chunk, ...args) {
    helperOutput.push(Buffer.isBuffer(chunk) ? chunk.toString("utf8") : String(chunk));
    return originalStdoutWrite.call(this, chunk, ...args);
  };
  process.stderr.write = function (chunk, ...args) {
    helperOutput.push(Buffer.isBuffer(chunk) ? chunk.toString("utf8") : String(chunk));
    return originalStderrWrite.call(this, chunk, ...args);
  };

  try {
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    const stagedJob = await releaseIdealTarget(evidence, output);

    const stagedContext = JSON.parse(await readFile(join(evidence, "context.json"), "utf8"));
    assert.equal(stagedContext.dossier, context.dossier);
    assert.deepEqual(stagedJob, {
      company: "Example",
      role: "Engineer",
      job_url: null,
      description: "Build APIs",
      user_instructions: "Emphasize backend delivery",
    });
    assert.equal(stagedContext.job.user_instructions, "Emphasize backend delivery");

    const previews = [];
    for (let index = 0; index < previewCount; index += 1) {
      if (index === 0) {
        // Intentionally not a locally valid CV shape: the server owns validation and normalization.
        await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "First draft", raw_content: "Created from the complete history" }));
      } else {
        const previous = JSON.parse(await readFile(join(output, "candidate.json"), "utf8"));
        if (!sameCandidateAcrossPreviews) {
          previous.title = `Revised draft ${index + 1}`;
          previous.sections[0].data.summary[0].items[0].text = `Improved target wording ${index + 1}`;
        }
        await writeFile(join(output, "candidate.json"), JSON.stringify(previous));
      }
      await writeFile(join(output, "RENDER"), "");
      const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.evaluation_id && !previews.some((item) => item.evaluation_id === value.evaluation_id));
      const canonicalOnDisk = JSON.parse(await readFile(join(output, "candidate.json"), "utf8"));
      assert.deepEqual(canonicalOnDisk, canonicalCandidate(previewBodies[index].candidate));
      assert.equal(canonicalOnDisk.sections[0].data.summary[0].id, "rtb_server_stable_01");
      const previewStatus = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "awaiting_revision_or_selection" && value.evaluation_id === preview.evaluation_id);
      assert.equal(previewStatus.candidate_hash, preview.candidate_hash);
      previews.push(preview);
    }

    if (reviewNotes) await writeFile(join(output, "review-notes.json"), JSON.stringify(reviewNotes));
    const reviewPackageAudits = [];
    const reviewStatuses = [];
    let latestSuccessfulReviewIndex;
    for (const reviewPreviewIndex of reviewPreviewIndices) {
      const reviewTarget = previews[reviewPreviewIndex];
      await writeFile(join(output, "selection.json"), JSON.stringify({
        evaluation_id: reviewTarget.evaluation_id,
        candidate_hash: reviewTarget.candidate_hash,
      }));
      await writeFile(join(output, "REVIEW"), "");
      const status = await waitForJson(join(output, "tailoring-status.json"), (value) => (
        value.state === "review_rejected"
        || (value.state === "review_package_ready" && value.evaluation_id === reviewTarget.evaluation_id)
      ));
      reviewStatuses.push(status);
      if (status.state === "review_rejected") break;
      latestSuccessfulReviewIndex = reviewPreviewIndex;
      const packageNames = (await readdir(status.package_directory)).sort();
      reviewPackageAudits.push({
        packageNames,
        pdfBytes: await readFile(join(status.package_directory, "candidate.pdf")),
        job: JSON.parse(await readFile(join(status.package_directory, "job.json"), "utf8")),
        manifest: JSON.parse(await readFile(join(status.package_directory, "manifest.json"), "utf8")),
        directory: status.package_directory,
      });
      await writeFile(join(output, "fit-review.json"), JSON.stringify(fitReviewFor(reviewTarget, reviewStatus)));
    }
    const selectedPreview = previews[selectedPreviewIndex];
    const selection = {
      evaluation_id: selectedPreview.evaluation_id,
      candidate_hash: wrongSelectionFirst ? "f".repeat(64) : selectedPreview.candidate_hash,
    };
    let reportTargetIndex = latestSuccessfulReviewIndex;
    if (reportTargetIndex === undefined) {
      await writeFile(join(output, "fit-review.json"), JSON.stringify(fitReviewFor(selectedPreview, "unavailable")));
      reportTargetIndex = selectedPreviewIndex;
    }
    await writeFile(join(output, "selection.json"), JSON.stringify(selection));
    await writeFile(join(output, "SUBMIT"), "");
    const staleReportSelection = reportTargetIndex !== selectedPreviewIndex;
    let staleReviewFailure = null;
    if (staleReportSelection) {
      staleReviewFailure = await waitForJson(join(output, "tailoring-status.json"), (value) => (
        value.state === "submit_rejected" && value.error?.includes("does not match the selected preview")
      ));
      await writeFile(join(output, "fit-review.json"), JSON.stringify(fitReviewFor(selectedPreview, "unavailable")));
      reportTargetIndex = selectedPreviewIndex;
      await writeFile(join(output, "SUBMIT"), "");
    }
    if (wrongSelectionFirst) {
      const failure = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "submit_rejected");
      assert.match(failure.error, /matching candidate_hash/);
      await writeFile(join(output, "selection.json"), JSON.stringify({
        evaluation_id: selectedPreview.evaluation_id,
        candidate_hash: selectedPreview.candidate_hash,
      }));
      await writeFile(join(output, "SUBMIT"), "");
    }
    if (firstSubmitStatus) {
      const failure = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "submit_rejected" && value.error?.includes(`HTTP ${firstSubmitStatus}`));
      assert.equal(failure.evaluation_id, selectedPreview.evaluation_id);
      await writeFile(join(output, "SUBMIT"), "");
    }

    const result = await resultPromise;
    const frozenCandidate = JSON.parse(await readFile(join(output, "attempts", selectedPreview.evaluation_id, "candidate.json"), "utf8"));
    const workspaceText = await allWorkspaceText(workspace);
    return {
      result,
      calls,
      previewBodies,
      submitBodies,
      previews,
      selectedPreview,
      frozenCandidate,
      workspaceText,
      helperOutput: helperOutput.join("\n"),
      reviewPackageAudits,
      reviewStatuses,
      staleReviewFailure,
    };
  } finally {
    process.stdout.write = originalStdoutWrite;
    process.stderr.write = originalStderrWrite;
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
}

test("session helper accepts only scoped Aergia session links", () => {
  assert.equal(PROTOCOL_VERSION, 10);
  assert.equal(serverOriginFromSessionUrl("https://aergia.example/agent/tailor/session-1"), "https://aergia.example");
  assert.equal(serverOriginFromSessionUrl("https://aergia.example/agent/tailor/session%2Done"), "https://aergia.example");
  assert.throws(() => serverOriginFromSessionUrl("https://aergia.example/applications"), /not an Aergia tailoring session/);
  assert.throws(() => serverOriginFromSessionUrl("javascript:alert(1)"), /safe HTTP\(S\)/);
  assert.throws(() => serverOriginFromSessionUrl("https://aergia.example/agent/tailor/session%2Fother"), /not an Aergia tailoring session/);
});

test("v10 withholds the dossier until an ideal target is complete, reserves an immutable preview, then explicitly submits it", { concurrency: false }, async () => {
  const { result, calls, previewBodies, submitBodies, selectedPreview, frozenCandidate, workspaceText, helperOutput } = await runComposerSession();
  assert.equal(result.status, "draft_ready");
  assert.deepEqual(calls.map((call) => call.path), [
    "/api/v1/tailoring/exchange",
    "/api/v1/tailoring/context",
    "/api/v1/tailoring/preview-reservations",
    "/api/v1/tailoring/preview",
    "/api/v1/tailoring/submit",
  ]);
  assert.equal(previewBodies[0].context_hash, "a".repeat(64));
  assert.ok(UUID_PATTERN.test(previewBodies[0].reservation_id));
  assert.deepEqual(frozenCandidate, canonicalCandidate(previewBodies[0].candidate));
  assert.equal(result.evaluation_id, selectedPreview.evaluation_id);
  const submit = submitBodies[0];
  assert.deepEqual(Object.keys(submit).sort(), ["candidate", "candidate_hash", "context_hash", "evaluation_id", "fit_review"]);
  assert.deepEqual(submit.candidate, frozenCandidate);
  assert.equal(submit.context_hash, "a".repeat(64));
  assert.equal(submit.evaluation_id, selectedPreview.evaluation_id);
  assert.equal(submit.candidate_hash, selectedPreview.candidate_hash);
  assert.equal(submit.fit_review.status, "unavailable");
  assert.equal(submit.fit_review.verdict, undefined);
  assert.equal(workspaceText.includes(capability), false);
  assert.equal(helperOutput.includes(makeContext().dossier), false);
  assert.doesNotMatch(workspaceText, /EDITORIAL_REVIEW|editorial-review|candidate-propositions|index-refresh/);
});

test("REVIEW exports only the exact selected PDF, allowlisted job fields, and three binding values", { concurrency: false }, async () => {
  const { result, previews, selectedPreview, submitBodies, reviewPackageAudits } = await runComposerSession({
    reviewPreviewIndices: [0],
  });
  const audit = reviewPackageAudits[0];
  assert.deepEqual(audit.packageNames, ["candidate.pdf", "job.json", "manifest.json"]);
  assert.deepEqual(audit.job, { company: "Example", role: "Engineer", description: "Build APIs" });
  assert.deepEqual(audit.manifest, {
    evaluation_id: previews[0].evaluation_id,
    candidate_hash: previews[0].candidate_hash,
    pdf_sha256: previews[0].pdf_sha256,
  });
  assert.deepEqual(audit.pdfBytes, Buffer.from("pdf-1"));
  assert.equal(createHash("sha256").update(audit.pdfBytes).digest("hex"), audit.manifest.pdf_sha256);
  assert.equal(submitBodies[0].fit_review.verdict, "generic");
  assert.equal(submitBodies[0].fit_review.evaluation_id, selectedPreview.evaluation_id);
  assert.equal(result.status, "draft_ready");
});

test("generic, unavailable, and explicitly skipped reports are advisory and submission uses the matching report", { concurrency: false }, async () => {
  for (const status of ["completed", "unavailable", "skipped_explicitly"]) {
    const { result, submitBodies } = await runComposerSession({ reviewPreviewIndices: [0], reviewStatus: status });
    assert.equal(result.status, "draft_ready");
    assert.equal(submitBodies[0].fit_review.status, status);
    assert.equal(submitBodies[0].fit_review.verdict, status === "completed" ? "generic" : undefined);
  }
});

test("a report for an older selection is rejected before the final selection is submitted as unavailable", { concurrency: false }, async () => {
  const { result, previews, selectedPreview, submitBodies, staleReviewFailure } = await runComposerSession({
    previewCount: 2,
    selectedPreviewIndex: 1,
    reviewPreviewIndices: [0],
  });
  assert.match(staleReviewFailure.error, /does not match the selected preview/);
  assert.equal(submitBodies.length, 1);
  assert.equal(submitBodies[0].evaluation_id, selectedPreview.evaluation_id);
  assert.equal(submitBodies[0].evaluation_id, previews[1].evaluation_id);
  assert.equal(submitBodies[0].fit_review.status, "unavailable");
});

test("allows one follow-up review only after the selected candidate hash changes", { concurrency: false }, async () => {
  const { previews, reviewStatuses, reviewPackageAudits, submitBodies } = await runComposerSession({
    previewCount: 2,
    selectedPreviewIndex: 1,
    reviewPreviewIndices: [0, 1, 0],
  });
  assert.notEqual(previews[0].candidate_hash, previews[1].candidate_hash);
  assert.deepEqual(reviewStatuses.map((status) => status.state), ["review_package_ready", "review_package_ready", "review_rejected"]);
  assert.equal(reviewPackageAudits.length, 2);
  assert.equal(submitBodies[0].fit_review.evaluation_id, previews[1].evaluation_id);
});

test("rejects a follow-up review when a new evaluation has the same candidate hash", { concurrency: false }, async () => {
  const { previews, reviewStatuses, reviewPackageAudits, submitBodies } = await runComposerSession({
    previewCount: 2,
    selectedPreviewIndex: 1,
    reviewPreviewIndices: [0, 1],
    sameCandidateAcrossPreviews: true,
  });
  assert.equal(previews[0].candidate_hash, previews[1].candidate_hash);
  assert.deepEqual(reviewStatuses.map((status) => status.state), ["review_package_ready", "review_rejected"]);
  assert.equal(reviewPackageAudits.length, 1);
  assert.equal(submitBodies[0].fit_review.status, "unavailable");
});

test("rejects exchange or context identities that do not match the supplied session link before writing evidence", { concurrency: false }, async () => {
  for (const mismatchAt of ["exchange", "context"]) {
    const workspace = await mkdtemp(join(tmpdir(), `aergia-tailor-wrong-${mismatchAt}-`));
    const evidence = join(workspace, "evidence");
    const context = makeContext();
    const calls = [];
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (url) => {
      const path = new URL(String(url)).pathname;
      calls.push(path);
      if (path.endsWith("/exchange")) {
        return Response.json({
          protocol_version: PROTOCOL_VERSION,
          session_id: mismatchAt === "exchange" ? "session-2" : "session-1",
          capability,
        });
      }
      if (path.endsWith("/context")) {
        return Response.json({ ...context, session_id: mismatchAt === "context" ? "session-2" : "session-1" });
      }
      throw new Error(`Unexpected request ${path}`);
    };
    try {
      const expectedError = mismatchAt === "exchange"
        ? /one-time code does not belong to the session in this link/
        : /returned context does not belong to the session in this link/;
      await assert.rejects(runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" }), expectedError);
      assert.deepEqual(calls, mismatchAt === "exchange"
        ? ["/api/v1/tailoring/exchange"]
        : ["/api/v1/tailoring/exchange", "/api/v1/tailoring/context"]);
      assert.deepEqual(await readdir(evidence), []);
    } finally {
      globalThis.fetch = originalFetch;
      await rm(workspace, { recursive: true, force: true });
    }
  }
});

test("stage zero accepts only a bounded, nonblank regular ideal target", { concurrency: false }, async () => {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-ideal-gate-"));
  const output = join(workspace, "output");
  const evidence = join(workspace, "evidence");
  const context = makeContext();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = withPreviewReservationRoutes(async (url) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/exchange")) return Response.json({ protocol_version: PROTOCOL_VERSION, session_id: "session-1", capability });
    if (path.endsWith("/context")) return Response.json(context);
    if (path.endsWith("/preview")) return Response.json({ code: "context_mismatch", detail: "The tailoring context changed; start a new session" }, { status: 409 });
    throw new Error(`Unexpected request ${path}`);
  });
  try {
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    await waitForJson(join(evidence, "job.json"), (value) => value.user_instructions === "Emphasize backend delivery");
    await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "awaiting_ideal_target");
    assert.deepEqual((await readdir(evidence)).sort(), ["job.json"]);

    const targetPath = join(output, "ideal-target.md");
    await mkdir(targetPath);
    const directoryStatus = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "ideal_target_invalid");
    assert.match(directoryStatus.error, /regular file/);
    await assert.rejects(readFile(join(evidence, "context.json"), "utf8"), { code: "ENOENT" });
    await rm(targetPath, { recursive: true });

    await writeIdealTargetAtomically(output, "x".repeat(1_048_577));
    const oversizedStatus = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "ideal_target_invalid" && /no larger than/.test(value.error));
    assert.match(oversizedStatus.error, /no larger than/);
    await assert.rejects(readFile(join(evidence, "context.json"), "utf8"), { code: "ENOENT" });

    await writeIdealTargetAtomically(output, " \n\t ");
    const blankStatus = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "ideal_target_invalid" && /blank/.test(value.error));
    assert.match(blankStatus.error, /blank/);
    await assert.rejects(readFile(join(evidence, "context.json"), "utf8"), { code: "ENOENT" });

    await writeIdealTargetAtomically(output);
    await waitForJson(join(evidence, "context.json"), (value) => value.protocol_version === PROTOCOL_VERSION);
    await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "Candidate", raw_content: "Supported draft" }));
    await writeFile(join(output, "RENDER"), "");
    await assert.rejects(resultPromise, /Start a new tailoring session/);
  } finally {
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
});

test("expires while waiting for the ideal target without revealing the dossier", { concurrency: false }, async () => {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-ideal-expiry-"));
  const output = join(workspace, "output");
  const evidence = join(workspace, "evidence");
  const context = makeContext();
  context.expires_at = new Date(Date.now() + 1_200).toISOString();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/exchange")) return Response.json({ protocol_version: PROTOCOL_VERSION, session_id: "session-1", capability });
    if (path.endsWith("/context")) return Response.json(context);
    throw new Error(`Unexpected request ${path}`);
  };
  try {
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    await waitForJson(join(evidence, "job.json"), (value) => value.company === "Example");
    await assert.rejects(resultPromise, /expired before the ideal target was completed/);
    const status = JSON.parse(await readFile(join(output, "tailoring-status.json"), "utf8"));
    assert.equal(status.state, "session_expired");
    assert.deepEqual((await readdir(evidence)).sort(), ["job.json"]);
    await assert.rejects(readFile(join(evidence, "context.json"), "utf8"), { code: "ENOENT" });
  } finally {
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
});

test("selects an earlier frozen canonical preview after a later edit", { concurrency: false }, async () => {
  const { result, previews, submitBodies, frozenCandidate } = await runComposerSession({
    previewCount: 2,
    selectedPreviewIndex: 0,
    reviewPreviewIndices: [0],
  });
  assert.notEqual(previews[0].evaluation_id, previews[1].evaluation_id);
  assert.notEqual(previews[0].candidate_hash, previews[1].candidate_hash);
  assert.equal(submitBodies.length, 1);
  assert.equal(submitBodies[0].evaluation_id, previews[0].evaluation_id);
  assert.equal(submitBodies[0].candidate_hash, previews[0].candidate_hash);
  assert.equal(submitBodies[0].fit_review.evaluation_id, previews[0].evaluation_id);
  assert.deepEqual(frozenCandidate, canonicalCandidate({ title: "First draft", raw_content: "Created from the complete history" }));
  assert.equal(result.evaluation_id, previews[0].evaluation_id);
});

test("optional review notes are sent without adding editorial review or runtime metadata", { concurrency: false }, async () => {
  const notes = [
    "Used a relevance-first project order because it better matches the target.",
    "😀".repeat(1_000),
  ];
  const { submitBodies } = await runComposerSession({ reviewNotes: notes });
  assert.deepEqual(submitBodies[0].review_notes, notes);
  assert.equal(Object.hasOwn(submitBodies[0], "editorial_review"), false);
  assert.equal(Object.hasOwn(submitBodies[0], "runtime_metrics"), false);
});

test("rejects a selection whose hash does not match the in-memory preview", { concurrency: false }, async () => {
  const { submitBodies, selectedPreview } = await runComposerSession({ wrongSelectionFirst: true });
  assert.equal(submitBodies.length, 1);
  assert.equal(submitBodies[0].evaluation_id, selectedPreview.evaluation_id);
  assert.equal(submitBodies[0].candidate_hash, selectedPreview.candidate_hash);
});

test("keeps the helper active after a recoverable submit error so the selected request can be retried", { concurrency: false }, async () => {
  const { submitBodies, result } = await runComposerSession({ firstSubmitStatus: 409 });
  assert.equal(submitBodies.length, 2);
  assert.deepEqual(submitBodies[0], submitBodies[1]);
  assert.equal(result.status, "draft_ready");
});

test("retries an identical frozen submit if the success response is lost", { concurrency: false }, async () => {
  const { submitBodies, result } = await runComposerSession({ loseFirstSubmitResponse: true });
  assert.equal(submitBodies.length, 2);
  assert.deepEqual(submitBodies[0], submitBodies[1]);
  assert.equal(result.status, "draft_ready");
});

test("refuses a non-empty workspace before exchanging the one-time code", { concurrency: false }, async () => {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-stale-"));
  await writeFile(join(workspace, "old-candidate.json"), "{}");
  const originalFetch = globalThis.fetch;
  let requestCount = 0;
  globalThis.fetch = async () => {
    requestCount += 1;
    throw new Error("unexpected network request");
  };
  try {
    await assert.rejects(runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" }), /empty workspace/);
    assert.equal(requestCount, 0);
  } finally {
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
});

test("stops when the server says the tailoring context is stale", { concurrency: false }, async () => {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-stale-context-"));
  const output = join(workspace, "output");
  const evidence = join(workspace, "evidence");
  const context = makeContext();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = withPreviewReservationRoutes(async (url) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/exchange")) return Response.json({ protocol_version: PROTOCOL_VERSION, session_id: "session-1", capability });
    if (path.endsWith("/context")) return Response.json(context);
    if (path.endsWith("/preview")) {
      return Response.json({ code: "context_mismatch", detail: "The tailoring context changed; start a new session" }, { status: 409 });
    }
    throw new Error(`Unexpected request ${path}`);
  });
  try {
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    await releaseIdealTarget(evidence, output);
    await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "Candidate" }));
    await writeFile(join(output, "RENDER"), "");
    await assert.rejects(resultPromise, /Start a new tailoring session/);
    const status = JSON.parse(await readFile(join(output, "tailoring-status.json"), "utf8"));
    assert.equal(status.state, "context_stale");
    assert.match(status.error, /target changed/);
  } finally {
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
});

test("preview access failures terminate without another preview or submit and without exposing the remote body", { concurrency: false }, async () => {
  for (const statusCode of [401, 403, 410]) {
    const workspace = await mkdtemp(join(tmpdir(), `aergia-tailor-preview-access-${statusCode}-`));
    const output = join(workspace, "output");
    const evidence = join(workspace, "evidence");
    const context = makeContext();
    const calls = [];
    const remoteSecret = `remote-secret-${statusCode}-must-not-appear`;
    const originalFetch = globalThis.fetch;
    globalThis.fetch = withPreviewReservationRoutes(async (url) => {
      const path = new URL(String(url)).pathname;
      calls.push(path);
      if (path.endsWith("/exchange")) return Response.json({ protocol_version: PROTOCOL_VERSION, session_id: "session-1", capability });
      if (path.endsWith("/context")) return Response.json(context);
      if (path.endsWith("/preview")) return Response.json({ detail: `Access revoked: ${remoteSecret}` }, { status: statusCode });
      if (path.endsWith("/submit")) throw new Error("Submit must not run after preview access is revoked");
      throw new Error(`Unexpected request ${path}`);
    }, (path) => calls.push(path));
    try {
      const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
      void resultPromise.catch(() => undefined);
      await releaseIdealTarget(evidence, output);
      await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "Candidate" }));
      await writeFile(join(output, "RENDER"), "");
      await assert.rejects(resultPromise, /Tailoring access expired or was revoked/);
      const status = JSON.parse(await readFile(join(output, "tailoring-status.json"), "utf8"));
      assert.equal(status.state, "access_expired_or_revoked");
      await writeFile(join(output, "RENDER"), "");
      await writeFile(join(output, "SUBMIT"), "");
      await sleep(50);
      assert.deepEqual(calls, [
        "/api/v1/tailoring/exchange",
        "/api/v1/tailoring/context",
        "/api/v1/tailoring/preview-reservations",
        "/api/v1/tailoring/preview",
      ]);
      assert.doesNotMatch(await allWorkspaceText(workspace), new RegExp(remoteSecret));
    } finally {
      globalThis.fetch = originalFetch;
      await rm(workspace, { recursive: true, force: true });
    }
  }
});

test("reservation acquisition, release, and submit access failures are terminal", { concurrency: false }, async () => {
  for (const stage of ["acquire", "release", "submit"]) {
    const workspace = await mkdtemp(join(tmpdir(), `aergia-tailor-${stage}-access-`));
    const output = join(workspace, "output");
    const evidence = join(workspace, "evidence");
    const context = makeContext();
    const calls = [];
    const statusCode = { acquire: 401, release: 403, submit: 410 }[stage];
    const remoteSecret = `remote-secret-${stage}-must-not-appear`;
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (url, options = {}) => {
      const path = new URL(String(url)).pathname;
      calls.push(path);
      if (path.endsWith("/exchange")) return Response.json({ protocol_version: PROTOCOL_VERSION, session_id: "session-1", capability });
      if (path.endsWith("/context")) return Response.json(context);
      if (path.endsWith("/preview-reservations")) {
        if (stage === "acquire") return Response.json({ detail: remoteSecret }, { status: statusCode });
        const body = JSON.parse(options.body);
        return Response.json({
          reservation_id: body.request_id,
          candidate_hash: sha(canonicalCandidate(body.candidate)),
          expires_at: new Date(Date.now() + 60_000).toISOString(),
        });
      }
      if (/\/preview-reservations\/[0-9a-f-]+\/release$/.test(path)) {
        return Response.json({ detail: remoteSecret }, { status: statusCode });
      }
      if (path.endsWith("/preview")) {
        if (stage === "release") return Response.json({});
        const candidate = canonicalCandidate(JSON.parse(options.body).candidate);
        const hash = sha(candidate);
        const pdfBytes = Buffer.from("access-stage-pdf");
        return Response.json({
          protocol_version: PROTOCOL_VERSION,
          candidate,
          format: "pdf",
          pdf_base64: pdfBytes.toString("base64"),
          pdf_sha256: createHash("sha256").update(pdfBytes).digest("hex"),
          page_count: 1,
          evaluation_id: "evaluation_0123456789abcdef",
          candidate_hash: hash,
          scanner_result: {},
          evaluation: { version: "tailoring-evaluation-v2", candidate_hash: hash },
          render_warnings: [],
        });
      }
      if (path.endsWith("/submit")) return Response.json({ detail: remoteSecret }, { status: statusCode });
      throw new Error(`Unexpected request ${path}`);
    };
    try {
      const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
      void resultPromise.catch(() => undefined);
      await releaseIdealTarget(evidence, output);
      await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "Candidate" }));
      await writeFile(join(output, "RENDER"), "");
      if (stage === "acquire" || stage === "release") {
        await assert.rejects(resultPromise, /Tailoring access expired or was revoked/);
      } else {
        const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.evaluation_id === "evaluation_0123456789abcdef");
        await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "awaiting_revision_or_selection");
        await writeFile(join(output, "selection.json"), JSON.stringify({
          evaluation_id: preview.evaluation_id,
          candidate_hash: preview.candidate_hash,
        }));
        await writeFile(join(output, "fit-review.json"), JSON.stringify(fitReviewFor(preview, "unavailable")));
        await writeFile(join(output, "SUBMIT"), "");
        await assert.rejects(resultPromise, /Tailoring access expired or was revoked/);
      }
      const status = JSON.parse(await readFile(join(output, "tailoring-status.json"), "utf8"));
      assert.equal(status.state, "access_expired_or_revoked");
      await writeFile(join(output, "RENDER"), "");
      await writeFile(join(output, "SUBMIT"), "");
      await sleep(50);
      assert.doesNotMatch(await allWorkspaceText(workspace), new RegExp(remoteSecret));
      assert.equal(calls.filter((path) => path.endsWith("/preview")).length, stage === "acquire" ? 0 : 1);
      assert.equal(calls.filter((path) => path.endsWith("/submit")).length, stage === "submit" ? 1 : 0);
      if (stage === "acquire") assert.equal(calls.some((path) => path.endsWith("/preview")), false);
      if (stage === "release") assert.equal(calls.some((path) => path.endsWith("/submit")), false);
    } finally {
      globalThis.fetch = originalFetch;
      await rm(workspace, { recursive: true, force: true });
    }
  }
});

test("keeps a transient preview transport failure separate and retries the same candidate", { concurrency: false }, async () => {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-preview-transient-"));
  const output = join(workspace, "output");
  const evidence = join(workspace, "evidence");
  const context = makeContext();
  const previewBodies = [];
  const submitBodies = [];
  let previewCount = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = withPreviewReservationRoutes(async (url, options = {}) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/exchange")) return Response.json({ protocol_version: PROTOCOL_VERSION, session_id: "session-1", capability });
    if (path.endsWith("/context")) return Response.json(context);
    if (path.endsWith("/preview")) {
      previewCount += 1;
      previewBodies.push(JSON.parse(options.body));
      if (previewCount === 1) throw new Error("transient transport details must stay private");
      const candidate = canonicalCandidate(previewBodies[1].candidate);
      const hash = sha(candidate);
      return Response.json({
        protocol_version: PROTOCOL_VERSION,
        candidate,
        format: "pdf",
        pdf_base64: Buffer.from("pdf").toString("base64"),
        pdf_sha256: createHash("sha256").update(Buffer.from("pdf")).digest("hex"),
        page_count: 1,
        evaluation_id: "evaluation_0123456789abcdef",
        candidate_hash: hash,
        scanner_result: {},
        evaluation: { version: "tailoring-evaluation-v2", candidate_hash: hash },
        render_warnings: [],
      });
    }
    if (path.endsWith("/submit")) {
      const body = JSON.parse(options.body);
      submitBodies.push(body);
      return Response.json({
        protocol_version: PROTOCOL_VERSION,
        status: "draft_ready",
        draft_cv_id: "draft-1",
        evaluation_id: body.evaluation_id,
        candidate_hash: body.candidate_hash,
        candidate: body.candidate,
        evaluation: { version: "tailoring-evaluation-v2", candidate_hash: body.candidate_hash },
      });
    }
    throw new Error(`Unexpected request ${path}`);
  });
  try {
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    await releaseIdealTarget(evidence, output);
    const candidate = { title: "Candidate after transport failure", raw_content: "Unchanged candidate" };
    await writeFile(join(output, "candidate.json"), JSON.stringify(candidate));
    await writeFile(join(output, "RENDER"), "");
    const recoverable = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "preview_recoverable_error");
    assert.doesNotMatch(recoverable.error, /transient transport details must stay private/);
    assert.doesNotMatch(await readFile(join(output, "candidate.json"), "utf8"), /Repair/);
    await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "A later edit that must not replace the frozen retry" }));
    await writeFile(join(output, "RENDER"), "");
    const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.evaluation_id === "evaluation_0123456789abcdef");
    await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "awaiting_revision_or_selection");
    await writeFile(join(output, "selection.json"), JSON.stringify({ evaluation_id: preview.evaluation_id, candidate_hash: preview.candidate_hash }));
    await writeFile(join(output, "fit-review.json"), JSON.stringify(fitReviewFor(preview, "unavailable")));
    await writeFile(join(output, "SUBMIT"), "");
    const result = await resultPromise;
    assert.equal(result.status, "draft_ready");
    assert.equal(previewCount, 2);
    assert.deepEqual(previewBodies[0], previewBodies[1]);
    assert.equal(textFromCandidate(previewBodies[1].candidate), "Unchanged candidate");
    assert.equal(submitBodies.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
});

test("retries a failed reservation with the same UUID and frozen candidate payload", { concurrency: false }, async () => {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-reservation-retry-"));
  const output = join(workspace, "output");
  const evidence = join(workspace, "evidence");
  const context = makeContext();
  const reservationBodies = [];
  const previewBodies = [];
  let reservationCount = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options = {}) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/exchange")) return Response.json({ protocol_version: PROTOCOL_VERSION, session_id: "session-1", capability });
    if (path.endsWith("/context")) return Response.json(context);
    if (path.endsWith("/preview-reservations")) {
      const body = JSON.parse(options.body);
      reservationBodies.push(body);
      reservationCount += 1;
      if (reservationCount === 1) throw new Error("temporary reservation transport details stay private");
      return Response.json({
        reservation_id: body.request_id,
        candidate_hash: sha(canonicalCandidate(body.candidate)),
        expires_at: new Date(Date.now() + 60_000).toISOString(),
      });
    }
    if (path.endsWith("/preview")) {
      const body = JSON.parse(options.body);
      previewBodies.push(body);
      const candidate = canonicalCandidate(body.candidate);
      const hash = sha(candidate);
      const bytes = Buffer.from("reservation-retry-pdf");
      return Response.json({
        candidate,
        format: "pdf",
        pdf_base64: bytes.toString("base64"),
        pdf_sha256: createHash("sha256").update(bytes).digest("hex"),
        page_count: 1,
        evaluation_id: "evaluation_0123456789abcdef",
        candidate_hash: hash,
        scanner_result: {},
        evaluation: { version: "tailoring-evaluation-v2", candidate_hash: hash },
        render_warnings: [],
      });
    }
    if (path.endsWith("/submit")) {
      const body = JSON.parse(options.body);
      return Response.json({
        protocol_version: PROTOCOL_VERSION,
        status: "draft_ready",
        draft_cv_id: "draft-1",
        evaluation_id: body.evaluation_id,
        candidate_hash: body.candidate_hash,
        candidate: body.candidate,
        evaluation: { version: "tailoring-evaluation-v2", candidate_hash: body.candidate_hash },
      });
    }
    throw new Error(`Unexpected request ${path}`);
  };
  try {
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    await releaseIdealTarget(evidence, output);
    const candidate = { title: "Frozen reservation candidate", raw_content: "Candidate body captured once" };
    await writeFile(join(output, "candidate.json"), JSON.stringify(candidate));
    await writeFile(join(output, "RENDER"), "");
    const recoverable = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "preview_recoverable_error");
    assert.doesNotMatch(recoverable.error, /temporary reservation transport details stay private/);
    await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "Changed after reservation failure" }));
    await writeFile(join(output, "RENDER"), "");
    const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.evaluation_id === "evaluation_0123456789abcdef");
    await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "awaiting_revision_or_selection");
    await writeFile(join(output, "selection.json"), JSON.stringify({
      evaluation_id: preview.evaluation_id,
      candidate_hash: preview.candidate_hash,
    }));
    await writeFile(join(output, "fit-review.json"), JSON.stringify(fitReviewFor(preview, "unavailable")));
    await writeFile(join(output, "SUBMIT"), "");
    const result = await resultPromise;

    assert.equal(result.status, "draft_ready");
    assert.equal(reservationBodies.length, 2);
    assert.deepEqual(reservationBodies[0], reservationBodies[1]);
    assert.ok(UUID_PATTERN.test(reservationBodies[0].request_id));
    assert.deepEqual(previewBodies, [{
      context_hash: context.context_hash,
      reservation_id: reservationBodies[0].request_id,
      candidate: reservationBodies[0].candidate,
    }]);
    assert.equal(textFromCandidate(previewBodies[0].candidate), "Candidate body captured once");
  } finally {
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
});

test("lets the agent submit a saved preview after the server declines another one", { concurrency: false }, async () => {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-preview-limit-"));
  const output = join(workspace, "output");
  const evidence = join(workspace, "evidence");
  const context = makeContext();
  const originalFetch = globalThis.fetch;
  let previewCount = 0;
  let submissionBody;
  globalThis.fetch = withPreviewReservationRoutes(async (url, options = {}) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/exchange")) return Response.json({ protocol_version: PROTOCOL_VERSION, session_id: "session-1", capability });
    if (path.endsWith("/context")) return Response.json(context);
    if (path.endsWith("/preview")) {
      previewCount += 1;
      if (previewCount > 1) return Response.json({ code: "preview_limit", detail: "The five-candidate-preview resource limit has been reached" }, { status: 409 });
      const candidate = canonicalCandidate(JSON.parse(options.body).candidate);
      const hash = sha(candidate);
      const pdfBytes = Buffer.from("pdf");
      return Response.json({
        candidate,
        format: "pdf",
        pdf_base64: pdfBytes.toString("base64"),
        pdf_sha256: createHash("sha256").update(pdfBytes).digest("hex"),
        page_count: 1,
        evaluation_id: "evaluation_0123456789abcdef",
        candidate_hash: hash,
        scanner_result: {},
        evaluation: { version: "tailoring-evaluation-v2", candidate_hash: hash },
        render_warnings: [],
      });
    }
    if (path.endsWith("/submit")) {
      submissionBody = JSON.parse(options.body);
      return Response.json({
        protocol_version: PROTOCOL_VERSION,
        status: "draft_ready",
        draft_cv_id: "draft-1",
        evaluation_id: submissionBody.evaluation_id,
        candidate_hash: submissionBody.candidate_hash,
        candidate: submissionBody.candidate,
        evaluation: { version: "tailoring-evaluation-v2", candidate_hash: submissionBody.candidate_hash },
      });
    }
    throw new Error(`Unexpected request ${path}`);
  });
  try {
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    await releaseIdealTarget(evidence, output);
    await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "First draft", raw_content: "First version" }));
    await writeFile(join(output, "RENDER"), "");
    const firstPreview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.evaluation_id === "evaluation_0123456789abcdef");
    await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "awaiting_revision_or_selection");
    const revision = JSON.parse(await readFile(join(output, "candidate.json"), "utf8"));
    revision.sections[0].data.summary[0].items[0].text = "A meaningful second version";
    await writeFile(join(output, "candidate.json"), JSON.stringify(revision));
    await writeFile(join(output, "RENDER"), "");
    const limitStatus = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "preview_limit_reached");
    assert.deepEqual(limitStatus.available_previews, [{
      evaluation_id: firstPreview.evaluation_id,
      candidate_hash: firstPreview.candidate_hash,
    }]);
    await writeFile(join(output, "selection.json"), JSON.stringify({
      evaluation_id: firstPreview.evaluation_id,
      candidate_hash: firstPreview.candidate_hash,
    }));
    await writeFile(join(output, "fit-review.json"), JSON.stringify(fitReviewFor(firstPreview, "unavailable")));
    await writeFile(join(output, "SUBMIT"), "");
    const result = await resultPromise;
    assert.equal(result.evaluation_id, firstPreview.evaluation_id);
    assert.equal(previewCount, 2);
    assert.equal(submissionBody.evaluation_id, firstPreview.evaluation_id);
    assert.deepEqual(submissionBody.candidate, canonicalCandidate({ title: "First draft", raw_content: "First version" }));
  } finally {
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
});

test("shows safe server validation locations and messages so a candidate can be repaired", { concurrency: false }, async () => {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-validation-error-"));
  const output = join(workspace, "output");
  const evidence = join(workspace, "evidence");
  const context = makeContext();
  const originalFetch = globalThis.fetch;
  let previewCount = 0;
  globalThis.fetch = withPreviewReservationRoutes(async (url, options = {}) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/exchange")) return Response.json({ protocol_version: PROTOCOL_VERSION, session_id: "session-1", capability });
    if (path.endsWith("/context")) return Response.json(context);
    if (path.endsWith("/preview")) {
      previewCount += 1;
      if (previewCount === 1) {
        return Response.json({
          detail: [{
            type: "missing",
            loc: ["body", "candidate", "sections"],
            msg: "Field required",
            input: { private_value: "must-not-be-echoed" },
          }],
        }, { status: 422 });
      }
      const candidate = canonicalCandidate(JSON.parse(options.body).candidate);
      const hash = sha(candidate);
      const pdfBytes = Buffer.from("pdf");
      return Response.json({
        candidate,
        format: "pdf",
        pdf_base64: pdfBytes.toString("base64"),
        pdf_sha256: createHash("sha256").update(pdfBytes).digest("hex"),
        page_count: 1,
        evaluation_id: "evaluation_0123456789abcdef",
        candidate_hash: hash,
        scanner_result: {},
        evaluation: { version: "tailoring-evaluation-v2", candidate_hash: hash },
        render_warnings: [],
      });
    }
    if (path.endsWith("/submit")) {
      const body = JSON.parse(options.body);
      return Response.json({
        protocol_version: PROTOCOL_VERSION,
        status: "draft_ready",
        draft_cv_id: "draft-1",
        evaluation_id: body.evaluation_id,
        candidate_hash: body.candidate_hash,
        candidate: body.candidate,
        evaluation: { version: "tailoring-evaluation-v2", candidate_hash: body.candidate_hash },
      });
    }
    throw new Error(`Unexpected request ${path}`);
  });
  try {
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    await releaseIdealTarget(evidence, output);
    await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "Invalid first attempt" }));
    await writeFile(join(output, "RENDER"), "");
    const validationStatus = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "candidate_or_preview_error");
    assert.match(validationStatus.error, /HTTP 422/);
    assert.doesNotMatch(validationStatus.error, /must-not-be-echoed|Field required/);
    await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "Repaired candidate", raw_content: "Complete and valid" }));
    await writeFile(join(output, "RENDER"), "");
    const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.evaluation_id === "evaluation_0123456789abcdef");
    await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "awaiting_revision_or_selection");
    await writeFile(join(output, "selection.json"), JSON.stringify({
      evaluation_id: preview.evaluation_id,
      candidate_hash: preview.candidate_hash,
    }));
    await writeFile(join(output, "fit-review.json"), JSON.stringify(fitReviewFor(preview, "unavailable")));
    await writeFile(join(output, "SUBMIT"), "");
    const result = await resultPromise;
    assert.equal(result.status, "draft_ready");
    assert.equal(previewCount, 2);
  } finally {
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
});
