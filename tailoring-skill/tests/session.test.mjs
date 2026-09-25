import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  PROTOCOL_VERSION,
  runSession,
  serverOriginFromSessionUrl,
  validateBatchPropositions,
  validateSourcePropositions,
} from "../skills/aergia-tailor/scripts/session.mjs";

const sha = (value) => createHash("sha256").update(JSON.stringify(value)).digest("hex");
const sleep = (duration = 25) => new Promise((resolve) => setTimeout(resolve, duration));

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

function makeContext(candidateIndex) {
  return {
    protocol_version: PROTOCOL_VERSION,
    evaluation_version: "tailoring-evaluation-v2",
    session_id: "session-1",
    application_id: "application-1",
    source_cv_id: null,
    expires_at: new Date(Date.now() + 60_000).toISOString(),
    context_hash: "a".repeat(64),
    job: { company: "Example", role: "Engineer", description: "Build APIs", user_instructions: null },
    profile: { name: "Ada" },
    previous_cv: null,
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
    candidate_index: candidateIndex,
    candidate_evidence: { schema_version: "candidate-evidence-v2", groups: [] },
    linked_cv_scan: null,
    opportunities: [],
    retrieved_sources: [],
    writer_context_characters: 0,
    effective_appearance: {},
    evaluation_version: "tailoring-evaluation-v2",
  };
}

const candidate = {
  title: "Platform Engineer",
  template_id: "generic-minimal",
  sections: [{ id: "profile", type: "profile", title: "Profile", enabled: true, data: { name: "Ada" } }],
  customizations: {},
};

const semanticContract = {
  proposition_extractor: "isolated-job-blind-worker",
  proposition_model: "isolated-worker",
  proposition_model_revision: "contract-managed",
  prompt_version: "candidate-proposition-prompt-v7",
  schema_version: "candidate-semantic-v1",
  extractor_version: "isolated-propositions-v1",
};

async function runComposerSession({ staleSources = [], failRefreshSubmit = false, previewCount = 1, selectedPreviewIndex = previewCount - 1, blockingReview = false, candidateSummary = null, firstSubmitStatus = null, loseFirstSubmitResponse = false } = {}) {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-v8-"));
  const output = join(workspace, "output");
  const evidence = join(workspace, "evidence");
  const extraction = join(workspace, "extraction");
  const candidateIndex = {
    schema_version: "candidate-index-v1",
    canonical_skills: [],
    source_count: staleSources.length,
    row_count: staleSources.length,
    semantic_source_counts: { fresh: 0, stale: 0, missing: staleSources.length },
    cache_state: staleSources.length ? "missing" : "warm",
  };
  const context = makeContext(candidateIndex);
  const indexResponse = {
    protocol_version: PROTOCOL_VERSION,
    stage: "candidate_index_refresh",
    session_id: context.session_id,
    expires_at: context.expires_at,
    cache_state: staleSources.length ? "missing" : "warm",
    source_counts: { fresh: 0, stale: 0, missing: staleSources.length },
    semantic_contract: semanticContract,
    sources: staleSources,
  };
  const calls = [];
  const submitBodies = [];
  let submitCount = 0;
  let savedSubmitResult = null;
  let outputBatch = null;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options = {}) => {
    const path = new URL(String(url)).pathname;
    calls.push({ path, options });
    if (path.endsWith("/exchange")) return Response.json({ protocol_version: PROTOCOL_VERSION, capability: "scoped-capability" });
    if (path.endsWith("/context/index-refresh") && options.method === "POST") {
      outputBatch = JSON.parse(options.body);
      if (failRefreshSubmit) return Response.json({ detail: "semantic refresh unavailable" }, { status: 503 });
      return Response.json({
        protocol_version: PROTOCOL_VERSION,
        stage: "candidate_index_refresh_result",
        session_id: context.session_id,
        expires_at: context.expires_at,
        accepted_source_ids: outputBatch.source_results.map((item) => item.source_id),
        rejected_source_ids: [],
        source_counts: { fresh: staleSources.length, stale: 0, missing: 0 },
      });
    }
    if (path.endsWith("/context/index-refresh")) return Response.json(indexResponse);
    if (path.endsWith("/context")) return Response.json(context);
    if (path.endsWith("/preview")) {
      const body = JSON.parse(options.body);
      const hash = sha(body.candidate);
      return Response.json({
        format: "pdf",
        pdf_base64: Buffer.from("pdf").toString("base64"),
        page_count: 1,
        evaluation_id: `evaluation_${String(calls.filter((call) => call.path.endsWith("/preview")).length).padStart(20, "0")}`,
        candidate_hash: hash,
        scanner_result: {},
        evaluation: {
          version: "tailoring-evaluation-v2",
          candidate_hash: hash,
          risk_findings: [],
          review_items: [],
          recommendations: [],
          regressions: [],
          non_actionable_gaps: [],
          improvements: [],
          dimensions: { job_fit: { candidate: 0.5 }, keywords: { candidate: 0.5 }, pdf_recovery: { candidate: 1 } },
        },
        render_warnings: [],
      });
    }
    if (path.endsWith("/submit")) {
      const body = JSON.parse(options.body);
      submitBodies.push(body);
      submitCount += 1;
      if (firstSubmitStatus && submitCount === 1) return Response.json({ detail: "temporary request issue; retry the selected attempt" }, { status: firstSubmitStatus });
      savedSubmitResult = savedSubmitResult ?? {
        protocol_version: PROTOCOL_VERSION,
        status: "draft_ready",
        draft_cv_id: "draft-1",
        evaluation_id: body.evaluation_id,
        candidate_hash: body.expected_candidate_hash,
        evaluation: {
          version: "tailoring-evaluation-v2",
          candidate_hash: body.expected_candidate_hash,
        },
      };
      if (loseFirstSubmitResponse && submitCount === 1) throw new Error("connection reset after the server saved the draft");
      return Response.json(savedSubmitResult);
    }
    throw new Error(`Unexpected request ${path}`);
  };

  try {
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);

    if (staleSources.length) {
      const batch = await waitForJson(join(extraction, "source-batch.json"), (value) => value.sources?.length === staleSources.length);
      assert.deepEqual(batch.semantic_contract, semanticContract);
      assert.doesNotMatch(JSON.stringify(batch), /job_description|linked_cv|target_strategy|scanner/i);
      const results = batch.sources.map((source) => ({
        source_id: source.source_id,
        source_fingerprint: source.source_fingerprint,
        claims: [],
      }));
      await writeFile(join(output, "candidate-propositions-batch.json"), JSON.stringify({
        schema_version: "candidate-proposition-batch-v2",
        results,
      }));
    }

    await waitForJson(join(evidence, "context.json"), (value) => value.protocol_version === PROTOCOL_VERSION);
    const previews = [];
    for (let index = 0; index < previewCount; index += 1) {
      const candidateWithSummary = candidateSummary
        ? { ...candidate, sections: [{ ...candidate.sections[0], data: { ...candidate.sections[0].data, summary: candidateSummary } }] }
        : candidate;
      const attemptCandidate = index === 0 ? candidateWithSummary : { ...candidateWithSummary, title: `${candidateWithSummary.title} ${index + 1}` };
      await writeFile(join(output, "candidate.json"), JSON.stringify(attemptCandidate));
      await writeFile(join(output, "RENDER"), "");
      const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.evaluation_id && !previews.some((item) => item.evaluation_id === value.evaluation_id));
      const review = {
        review_version: "aergia-editorial-review-v2",
        evaluation_id: preview.evaluation_id,
        candidate_hash: preview.candidate_hash,
        findings: [],
      };
      if (blockingReview && index === 0) review.findings = [{
        category: "framing",
        severity: "blocking",
        section_id: "profile",
        excerpt: "Ada",
        problem: "The review initially marked a concern that is not in the candidate.",
        recommended_change: "Correct the mistaken review finding.",
      }];
      await writeFile(join(output, "editorial-review.json"), JSON.stringify(review));
      await writeFile(join(output, "EDITORIAL_REVIEW"), "");
      const reviewedStatus = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "awaiting_agent_decision" && value.evaluation_id === preview.evaluation_id);
      assert.equal(reviewedStatus.candidate_hash, preview.candidate_hash);
      previews.push(preview);
    }
    const selectedPreview = previews[selectedPreviewIndex];
    await writeFile(join(output, "selection.json"), JSON.stringify({ evaluation_id: selectedPreview.evaluation_id, candidate_hash: selectedPreview.candidate_hash }));
    await writeFile(join(output, "SUBMIT"), "");
    if (firstSubmitStatus) {
      const failure = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "submit_rejected" && value.error?.includes(`HTTP ${firstSubmitStatus}`));
      assert.equal(failure.evaluation_id, selectedPreview.evaluation_id);
      await writeFile(join(output, "SUBMIT"), "");
    }
    const result = await resultPromise;
    const metrics = JSON.parse(await readFile(join(output, "runtime-metrics.json"), "utf8"));
    const frozenCandidate = JSON.parse(await readFile(join(output, "attempts", selectedPreview.evaluation_id, "candidate.json"), "utf8"));
    return { result, calls, outputBatch, metrics, previews, selectedPreview, frozenCandidate, submitBodies };
  } finally {
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
}

test("session helper accepts only scoped Aergia session links", () => {
  assert.equal(serverOriginFromSessionUrl("https://aergia.example/agent/tailor/session-1"), "https://aergia.example");
  assert.throws(() => serverOriginFromSessionUrl("https://aergia.example/applications"), /not an Aergia tailoring session/);
  assert.throws(() => serverOriginFromSessionUrl("javascript:alert(1)"), /safe HTTP\(S\)/);
});

test("semantic batch validation keeps valid peers and rejects bad IDs, fingerprints, and claims", () => {
  const a = { source_id: "source_a", source_fingerprint: "a".repeat(64) };
  const b = { source_id: "source_b", source_fingerprint: "b".repeat(64) };
  const c = { source_id: "source_c", source_fingerprint: "c".repeat(64) };
  const result = validateBatchPropositions({
    schema_version: "candidate-proposition-batch-v2",
    results: [
      { ...a, claims: [] },
      { ...b, source_fingerprint: "d".repeat(64), claims: [] },
      { source_id: "source_unknown", source_fingerprint: "d".repeat(64), claims: [] },
      { ...c, claims: [{ statement: "bad claim", support: "inferred", source_excerpt: "evidence", associated_concepts: [] }] },
    ],
  }, [a, b, c]);
  assert.deepEqual(result.map((item) => item.source_id), ["source_a"]);

  const claim = {
    statement: "Deployed containerized applications",
    support: "explicit",
    source_excerpt: "Deployed containerized applications with Docker.",
    associated_concepts: [],
  };
  assert.equal(validateSourcePropositions({ ...a, claims: [claim] }, a.source_id, a.source_fingerprint).claims.length, 1);
  assert.throws(() => validateSourcePropositions({ ...a, claims: [claim] }, a.source_id, "f".repeat(64)), /fingerprint/);
});

test("warm protocol v8 session keeps and submits the explicitly selected frozen preview", { concurrency: false }, async () => {
  const { result, calls, outputBatch, metrics, selectedPreview, frozenCandidate, submitBodies } = await runComposerSession();
  assert.equal(result.status, "draft_ready");
  assert.equal(outputBatch, null);
  assert.deepEqual(calls.map((call) => call.path), [
    "/api/v1/tailoring/exchange",
    "/api/v1/tailoring/context/index-refresh",
    "/api/v1/tailoring/context",
    "/api/v1/tailoring/preview",
    "/api/v1/tailoring/submit",
  ]);
  assert.equal(metrics.candidate_cue_calls, 0);
  assert.equal(metrics.semantic_indexing_calls, 0);
  assert.equal(metrics.indexing_workers, 0);
  assert.equal(metrics.main_writer_calls, 1);
  assert.equal(result.evaluation_id, selectedPreview.evaluation_id);
  assert.deepEqual(frozenCandidate, candidate);
  const submit = calls.find((call) => call.path.endsWith("/submit"));
  const submitBody = JSON.parse(submit.options.body);
  assert.equal(submitBody.evaluation_id, selectedPreview.evaluation_id);
  assert.equal(submitBody.expected_candidate_hash, selectedPreview.candidate_hash);
  assert.equal(Object.hasOwn(submitBody, "allow_bounded_fallback"), false);
  assert.deepEqual(submitBodies, [submitBody]);
});

test("selects an earlier frozen preview when a later attempt changes", { concurrency: false }, async () => {
  const { result, previews, submitBodies, frozenCandidate } = await runComposerSession({ previewCount: 2, selectedPreviewIndex: 0 });
  assert.notEqual(previews[0].evaluation_id, previews[1].evaluation_id);
  assert.notEqual(previews[0].candidate_hash, previews[1].candidate_hash);
  assert.equal(submitBodies.length, 1);
  assert.equal(submitBodies[0].evaluation_id, previews[0].evaluation_id);
  assert.equal(submitBodies[0].expected_candidate_hash, previews[0].candidate_hash);
  assert.equal(Object.hasOwn(submitBodies[0], "inference_notes"), false);
  assert.deepEqual(frozenCandidate, candidate);
  assert.equal(result.evaluation_id, previews[0].evaluation_id);
});

test("keeps the helper running after a recoverable submit error so the agent can retry", { concurrency: false }, async () => {
  const { calls, submitBodies, result } = await runComposerSession({ firstSubmitStatus: 409 });
  const posts = calls.filter((call) => call.path.endsWith("/submit"));
  assert.equal(posts.length, 2);
  assert.deepEqual(submitBodies[0], submitBodies[1]);
  assert.equal(result.status, "draft_ready");
});

test("retries an identical submit after the success response is lost", { concurrency: false }, async () => {
  const { calls, submitBodies, result } = await runComposerSession({ loseFirstSubmitResponse: true });
  const posts = calls.filter((call) => call.path.endsWith("/submit"));
  assert.equal(posts.length, 2);
  assert.deepEqual(submitBodies[0], submitBodies[1]);
  assert.equal(result.status, "draft_ready");
});

test("submits inferred target-relevant prose without a claim audit", { concurrency: false }, async () => {
  const summary = "Client-facing software development with testing and QA experience";
  const { selectedPreview, submitBodies, frozenCandidate, result } = await runComposerSession({ candidateSummary: summary });
  assert.equal(frozenCandidate.sections[0].data.summary, summary);
  assert.equal(result.status, "draft_ready");
  assert.equal(submitBodies[0].evaluation_id, selectedPreview.evaluation_id);
  assert.equal(submitBodies[0].expected_candidate_hash, selectedPreview.candidate_hash);
  assert.equal(Object.hasOwn(submitBodies[0], "inference_notes"), false);
});

test("submits a selected evaluation when editorial findings are advisory", { concurrency: false }, async () => {
  const { calls, selectedPreview, result } = await runComposerSession({ blockingReview: true });
  assert.equal(calls.filter((call) => call.path.endsWith("/preview")).length, 1);
  assert.equal(result.evaluation_id, selectedPreview.evaluation_id);
});

test("one stale source is isolated, refreshed, and submitted as one bounded worker batch", { concurrency: false }, async () => {
  const staleSources = [{
    source_id: "source_a",
    source_fingerprint: "a".repeat(64),
    kind: "experience",
    identity: { company: "Example" },
    structured_facts: {},
    narrative: "Built Python services.",
  }];
  const { result, calls, outputBatch, metrics } = await runComposerSession({ staleSources });
  assert.equal(result.status, "draft_ready");
  assert.deepEqual(outputBatch.source_results, [{
    source_id: "source_a",
    source_fingerprint: "a".repeat(64),
    claims: [],
  }]);
  assert.equal(calls.filter((call) => call.path.endsWith("/context/index-refresh")).length, 2);
  assert.equal(metrics.candidate_cue_calls, 0);
  assert.equal(metrics.semantic_indexing_calls, 1);
  assert.equal(metrics.semantic_batches_processed, 1);
  assert.equal(metrics.indexing_workers, 1);
});

test("failed semantic persistence falls back to deterministic context and continues composition", { concurrency: false }, async () => {
  const staleSources = [{
    source_id: "source_stale",
    source_fingerprint: "c".repeat(64),
    kind: "experience",
    identity: { company: "Example" },
    structured_facts: {},
    narrative: "Built Python APIs.",
  }];
  const { result, calls, outputBatch } = await runComposerSession({ staleSources, failRefreshSubmit: true });
  assert.equal(result.status, "draft_ready");
  assert.equal(outputBatch.source_results[0].source_id, "source_stale");
  assert.ok(calls.some((call) => call.path.endsWith("/context")));
});
