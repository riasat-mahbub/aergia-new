import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { runSession, serverOriginFromSessionUrl } from "../skills/aergia-tailor/scripts/session.mjs";

const candidateHash = (candidate) => createHash("sha256").update(JSON.stringify(candidate)).digest("hex");

const evaluation = (hash, pass, status = "ready_with_review", recommendationCount = 0) => ({
  version: "tailoring-evaluation-v1",
  candidate_hash: hash,
  pass_number: pass,
  source_comparison: { available: false, requirement_transitions: [], keyword_transitions: [] },
  previous_pass_comparison: { available: false, previous_candidate_hash: null, candidate_hash: hash, changes: [], job_fit_delta: null, term_visibility_delta: null },
  dimensions: {
    job_fit: { source: 0.45, candidate: 0.52 },
    keywords: { source: 0.2, candidate: 0.4 },
    ats: { source_count: 0, candidate_count: 0, candidate_error_count: 0, candidate_warning_count: 0, candidate_info_count: 0 },
    resume_quality: { source_count: 0, candidate_count: 0, candidate_error_count: 0, candidate_warning_count: 0, candidate_info_count: 0 },
    pdf_recovery: { source: null, candidate: 0.99 },
  },
  improvements: [],
  regressions: [],
  blockers: [],
  review_items: [],
  recommendations: Array.from({ length: recommendationCount }, (_, index) => ({
    id: `recommendation-${index}`,
    kind: "recommendation",
    category: "lexical",
    message: `Review recommendation ${index + 1}`,
    detail: null,
    priority: "normal",
    requirement_id: null,
    term_id: null,
    code: null,
    importance: null,
  })),
  non_actionable_gaps: [],
  inference_notes: [],
  render_warnings: [],
  readiness: {
    status,
    submission_allowed: status === "ready" || status === "ready_with_review",
    reasons: status === "revise" ? ["A concrete fixable issue remains."] : ["The candidate is available for review."],
  },
});

const editorialReview = (hash, pass, inferenceNotes = []) => ({
  review_version: "aergia-editorial-review-v1",
  candidate_hash: hash,
  pass_number: pass,
  findings: [],
  inference_notes: inferenceNotes,
});

async function waitForJson(path, predicate, timeoutMs = 8_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const parsed = JSON.parse(await readFile(path, "utf8"));
      if (predicate(parsed)) return parsed;
    } catch {
      // The helper may be atomically replacing this status file.
    }
    await new Promise((accept) => setTimeout(accept, 25));
  }
  throw new Error("Timed out waiting for " + path);
}

async function makeSessionWorkspace() {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-session-"));
  const context = {
    protocol_version: 5,
    evaluation_version: "tailoring-evaluation-v1",
    session_id: "session-1",
    application_id: "application-1",
    source_cv_id: null,
    expires_at: new Date(Date.now() + 20_000).toISOString(),
    context_hash: "a".repeat(64),
    job: { company: "Example", role: "Engineer", description: "Build APIs", user_instructions: null },
    profile: { name: "Ada" },
    previous_cv: null,
    library: [],
    scanner: {
      schema_version: "scanner-v1",
      versions: {},
      requirement_extraction: { requirements: [] },
      source_scan: null,
    },
    requirements: [],
    templates: [{ id: "generic-minimal", manifest: {} }],
    selected_template_id: "generic-minimal",
    selected_template_manifest: {},
    capabilities: {},
    capabilities_hash: "b".repeat(64),
    effective_appearance: {},
  };
  const candidate = {
    title: "Platform Engineer",
    template_id: "generic-minimal",
    sections: [{ id: "profile", type: "profile", title: "Profile", enabled: true, data: { name: "Ada" } }],
    customizations: {},
  };
  const output = join(workspace, "output");
  await mkdir(output, { recursive: true });
  await writeFile(join(output, "candidate.json"), JSON.stringify(candidate));
  return { workspace, output, context, candidate };
}

function mockTailoringServer(context, evaluator = ({ candidate, pass }) => evaluation(candidateHash(candidate), pass)) {
  const calls = [];
  let previewNumber = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url: String(url), options });
    if (String(url).endsWith("/exchange")) return Response.json({ protocol_version: 5, capability: "scoped-capability" });
    if (String(url).endsWith("/context")) return Response.json(context);
    if (String(url).endsWith("/preview")) {
      previewNumber += 1;
      const body = JSON.parse(options.body);
      const hash = candidateHash(body.candidate);
      return Response.json({
        format: "pdf",
        pdf_base64: Buffer.from("pdf-" + previewNumber).toString("base64"),
        page_count: 1,
        candidate_hash: hash,
        scanner_result: { schema_version: "scanner-v1", semantic: { summary: { job_fit: 0.52 } } },
        evaluation: evaluator({ candidate: body.candidate, pass: previewNumber, hash }),
        render_warnings: [],
      });
    }
    const submitBody = JSON.parse(options.body);
    return Response.json({
      protocol_version: 5,
      status: "draft_ready",
      draft_cv_id: "draft-1",
      candidate_hash: submitBody.expected_candidate_hash,
      scanner_result: {},
      evaluation: evaluator({ candidate: submitBody.candidate, pass: previewNumber, hash: submitBody.expected_candidate_hash }),
      render_warnings: [],
    });
  };
  return { calls, restore: () => { globalThis.fetch = originalFetch; } };
}

test("session helper accepts only scoped Aergia session links", { concurrency: false }, () => {
  assert.equal(serverOriginFromSessionUrl("https://aergia.example/agent/tailor/session-1"), "https://aergia.example");
  assert.throws(() => serverOriginFromSessionUrl("https://aergia.example/applications"), /not an Aergia tailoring session/);
  assert.throws(() => serverOriginFromSessionUrl("javascript:alert(1)"), /safe HTTP\(S\)/);
});

test("session helper submits an exact reviewed candidate and carries inference notes", { concurrency: false }, async () => {
  const { workspace, output, context, candidate } = await makeSessionWorkspace();
  const server = mockTailoringServer(context);
  try {
    const source = join(workspace, "source");
    await mkdir(source, { recursive: true });
    const notes = [{ claim: "Jest familiarity", basis: ["React/TypeScript work", "documented unit testing"], confidence: "reasonable", review_recommended: true }];
    await writeFile(join(output, "inference-notes.json"), JSON.stringify(notes));
    await writeFile(join(output, "RENDER"), "");
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.pass_number === 1);
    assert.equal(preview.evaluation.readiness.status, "ready_with_review");
    await writeFile(join(output, "editorial-review.json"), JSON.stringify(editorialReview(preview.candidate_hash, 1, notes)));
    await writeFile(join(output, "EDITORIAL_REVIEW"), "");
    await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "ready_for_submission");

    await writeFile(join(output, "candidate.json"), JSON.stringify({ ...candidate, title: "Edited after preview" }));
    await writeFile(join(output, "SUBMIT"), "");
    const rejected = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "submit_rejected");
    assert.match(rejected.error, /exact reviewed non-blocked candidate|candidate changed/);
    assert.equal(server.calls.filter((call) => call.url.endsWith("/submit")).length, 0);

    await writeFile(join(output, "candidate.json"), JSON.stringify(candidate));
    await writeFile(join(output, "SUBMIT"), "");
    const result = await resultPromise;
    assert.equal(result.status, "draft_ready");
    assert.equal(server.calls.length, 4);
    assert.equal(server.calls[1].options.headers["X-Aergia-Tailoring-Capability"], "scoped-capability");
    const body = JSON.parse(server.calls[3].options.body);
    assert.deepEqual(body.inference_notes, notes);
    assert.deepEqual(body.editorial_review.inference_notes, notes);
    assert.equal(body.allow_bounded_fallback, false);
    assert.doesNotMatch(await readFile(join(output, "result.json"), "utf8"), /scoped-capability/);
    assert.doesNotMatch(await readFile(join(source, "context.json"), "utf8"), /scoped-capability/);
  } finally {
    server.restore();
    await rm(workspace, { recursive: true, force: true });
  }
});

test("five revise passes use issue-based best-candidate fallback, not score maximization", { concurrency: false }, async () => {
  const { workspace, output, context, candidate } = await makeSessionWorkspace();
  const recommendationCounts = [3, 2, 1, 2, 2];
  const server = mockTailoringServer(context, ({ pass, hash }) => {
    const result = evaluation(hash, pass, pass === 5 ? "blocked" : "revise", recommendationCounts[pass - 1] ?? 1);
    result.dimensions.job_fit.candidate = pass === 5 ? 0.9 : 0.6;
    if (pass === 5) {
      result.blockers = [{
        id: "pdf-critical-text_retention",
        kind: "blocker",
        category: "pdf_recovery",
        message: "Rendered text retention failed.",
        detail: null,
        priority: "high",
        requirement_id: null,
        term_id: null,
        code: "text_retention",
        importance: null,
      }];
      result.readiness.reasons = ["Rendered text retention failed."];
    }
    return result;
  });
  try {
    await writeFile(join(output, "RENDER"), "");
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    let bestTitle = null;
    for (let pass = 1; pass <= 5; pass += 1) {
      const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.pass_number === pass);
      await writeFile(join(output, "editorial-review.json"), JSON.stringify(editorialReview(preview.candidate_hash, pass)));
      await writeFile(join(output, "EDITORIAL_REVIEW"), "");
      await waitForJson(join(output, "tailoring-status.json"), (value) => value.pass_number === pass && (pass < 5 ? value.state === "revision_required" : value.state === "fallback_available"));
      if (pass === 3) bestTitle = "Candidate pass 3";
      if (pass < 5) {
        await writeFile(join(output, "candidate.json"), JSON.stringify({ ...candidate, title: `Candidate pass ${pass + 1}` }));
        await writeFile(join(output, "RENDER"), "");
      }
    }
    await writeFile(join(output, "SUBMIT"), "");
    await resultPromise;
    const submitCall = server.calls.find((call) => call.url.endsWith("/submit"));
    assert.ok(submitCall);
    const body = JSON.parse(submitCall.options.body);
    assert.equal(body.candidate.title, bestTitle);
    assert.equal(body.allow_bounded_fallback, true);
    assert.ok(body.review_notes.some((note) => /five-pass evaluation limit/.test(note)));
    assert.equal(server.calls.filter((call) => call.url.endsWith("/preview")).length, 5);
  } finally {
    server.restore();
    await rm(workspace, { recursive: true, force: true });
  }
});

test("repeated candidates stop early and cannot trigger another preview", { concurrency: false }, async () => {
  const { workspace, output, context, candidate } = await makeSessionWorkspace();
  const server = mockTailoringServer(context, ({ pass, hash }) => evaluation(hash, pass, "revise", 1));
  try {
    await writeFile(join(output, "RENDER"), "");
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    for (let pass = 1; pass <= 2; pass += 1) {
      const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.pass_number === pass);
      await writeFile(join(output, "editorial-review.json"), JSON.stringify(editorialReview(preview.candidate_hash, pass)));
      await writeFile(join(output, "EDITORIAL_REVIEW"), "");
      await waitForJson(join(output, "tailoring-status.json"), (value) => value.pass_number === pass && value.state === (pass === 1 ? "revision_required" : "fallback_available"));
      if (pass === 1) await writeFile(join(output, "RENDER"), "");
    }
    const stopped = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "fallback_available");
    assert.equal(stopped.stop_reason, "repeated_candidate");
    await writeFile(join(output, "SUBMIT"), "");
    await resultPromise;
    assert.equal(server.calls.filter((call) => call.url.endsWith("/preview")).length, 2);
    const submitCall = server.calls.find((call) => call.url.endsWith("/submit"));
    assert.equal(JSON.parse(submitCall.options.body).candidate.title, candidate.title);
  } finally {
    server.restore();
    await rm(workspace, { recursive: true, force: true });
  }
});

test("persistent blockers stop after two meaningful unchanged revisions", { concurrency: false }, async () => {
  const { workspace, output, context, candidate } = await makeSessionWorkspace();
  const server = mockTailoringServer(context, ({ pass, hash }) => {
    const blocked = evaluation(hash, pass, "blocked");
    blocked.blockers = [{
      id: "pdf-critical-text_retention",
      kind: "blocker",
      category: "pdf_recovery",
      message: "Rendered text retention failed.",
      detail: null,
      priority: "high",
      requirement_id: null,
      term_id: null,
      code: "text_retention",
      importance: null,
    }];
    blocked.readiness.reasons = ["Rendered text retention failed."];
    return blocked;
  });
  try {
    await writeFile(join(output, "RENDER"), "");
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    for (let pass = 1; pass <= 3; pass += 1) {
      const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.pass_number === pass);
      await writeFile(join(output, "editorial-review.json"), JSON.stringify(editorialReview(preview.candidate_hash, pass)));
      await writeFile(join(output, "EDITORIAL_REVIEW"), "");
      const expectedState = pass === 3 ? "blocked" : "blocked";
      await waitForJson(join(output, "tailoring-status.json"), (value) => value.pass_number === pass && value.state === expectedState && (pass < 3 || value.stop_reason === "unchanged_blockers"));
      if (pass < 3) {
        await writeFile(join(output, "candidate.json"), JSON.stringify({ ...candidate, title: `Blocked pass ${pass + 1}` }));
        await writeFile(join(output, "RENDER"), "");
      }
    }
    await assert.rejects(resultPromise, /unresolved blocking issues/);
    assert.equal(server.calls.filter((call) => call.url.endsWith("/preview")).length, 3);
    assert.equal(server.calls.filter((call) => call.url.endsWith("/submit")).length, 0);
  } finally {
    server.restore();
    await rm(workspace, { recursive: true, force: true });
  }
});
