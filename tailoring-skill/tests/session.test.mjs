import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
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

async function runComposerSession({
  previewCount = 1,
  selectedPreviewIndex = previewCount - 1,
  firstSubmitStatus = null,
  loseFirstSubmitResponse = false,
  reviewNotes = null,
  wrongSelectionFirst = false,
} = {}) {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-v9-"));
  const output = join(workspace, "output");
  const evidence = join(workspace, "evidence");
  const context = makeContext();
  const calls = [];
  const previewBodies = [];
  const submitBodies = [];
  let submitCount = 0;
  let savedSubmitResult = null;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options = {}) => {
    const path = new URL(String(url)).pathname;
    calls.push({ path, options });
    if (path.endsWith("/exchange")) {
      return Response.json({ protocol_version: PROTOCOL_VERSION, capability });
    }
    if (path.endsWith("/context")) return Response.json(context);
    if (path.endsWith("/preview")) {
      const body = JSON.parse(options.body);
      previewBodies.push(body);
      const candidate = canonicalCandidate(body.candidate);
      const hash = sha(candidate);
      const evaluationId = `evaluation_${String(previewBodies.length).padStart(20, "0")}`;
      return Response.json({
        protocol_version: PROTOCOL_VERSION,
        candidate,
        format: "pdf",
        pdf_base64: Buffer.from(`pdf-${previewBodies.length}`).toString("base64"),
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

  try {
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    await waitForJson(join(evidence, "context.json"), (value) => value.protocol_version === PROTOCOL_VERSION);

    const stagedContext = JSON.parse(await readFile(join(evidence, "context.json"), "utf8"));
    assert.equal(stagedContext.dossier, context.dossier);
    assert.equal(stagedContext.job.user_instructions, "Emphasize backend delivery");

    const previews = [];
    for (let index = 0; index < previewCount; index += 1) {
      if (index === 0) {
        // Intentionally not a locally valid CV shape: the server owns validation and normalization.
        await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "First draft", raw_content: "Created from the complete history" }));
      } else {
        const previous = JSON.parse(await readFile(join(output, "candidate.json"), "utf8"));
        previous.title = `Revised draft ${index + 1}`;
        previous.sections[0].data.summary[0].items[0].text = `Improved target wording ${index + 1}`;
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
    const selectedPreview = previews[selectedPreviewIndex];
    const selection = {
      evaluation_id: selectedPreview.evaluation_id,
      candidate_hash: wrongSelectionFirst ? "f".repeat(64) : selectedPreview.candidate_hash,
    };
    await writeFile(join(output, "selection.json"), JSON.stringify(selection));
    await writeFile(join(output, "SUBMIT"), "");
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
    return { result, calls, previewBodies, submitBodies, previews, selectedPreview, frozenCandidate, workspaceText };
  } finally {
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
}

test("session helper accepts only scoped Aergia session links", () => {
  assert.equal(PROTOCOL_VERSION, 9);
  assert.equal(serverOriginFromSessionUrl("https://aergia.example/agent/tailor/session-1"), "https://aergia.example");
  assert.throws(() => serverOriginFromSessionUrl("https://aergia.example/applications"), /not an Aergia tailoring session/);
  assert.throws(() => serverOriginFromSessionUrl("javascript:alert(1)"), /safe HTTP\(S\)/);
});

test("v9 fetches one complete dossier, freezes the canonical preview, and binds explicit submission", { concurrency: false }, async () => {
  const { result, calls, previewBodies, submitBodies, selectedPreview, frozenCandidate, workspaceText } = await runComposerSession();
  assert.equal(result.status, "draft_ready");
  assert.deepEqual(calls.map((call) => call.path), [
    "/api/v1/tailoring/exchange",
    "/api/v1/tailoring/context",
    "/api/v1/tailoring/preview",
    "/api/v1/tailoring/submit",
  ]);
  assert.equal(previewBodies[0].context_hash, "a".repeat(64));
  assert.deepEqual(frozenCandidate, canonicalCandidate(previewBodies[0].candidate));
  assert.equal(result.evaluation_id, selectedPreview.evaluation_id);
  const submit = submitBodies[0];
  assert.deepEqual(Object.keys(submit).sort(), ["candidate", "candidate_hash", "context_hash", "evaluation_id"]);
  assert.deepEqual(submit.candidate, frozenCandidate);
  assert.equal(submit.context_hash, "a".repeat(64));
  assert.equal(submit.evaluation_id, selectedPreview.evaluation_id);
  assert.equal(submit.candidate_hash, selectedPreview.candidate_hash);
  assert.equal(workspaceText.includes(capability), false);
  assert.doesNotMatch(workspaceText, /EDITORIAL_REVIEW|editorial-review|candidate-propositions|index-refresh/);
});

test("selects an earlier frozen canonical preview after a later edit", { concurrency: false }, async () => {
  const { result, previews, submitBodies, frozenCandidate } = await runComposerSession({ previewCount: 2, selectedPreviewIndex: 0 });
  assert.notEqual(previews[0].evaluation_id, previews[1].evaluation_id);
  assert.notEqual(previews[0].candidate_hash, previews[1].candidate_hash);
  assert.equal(submitBodies.length, 1);
  assert.equal(submitBodies[0].evaluation_id, previews[0].evaluation_id);
  assert.equal(submitBodies[0].candidate_hash, previews[0].candidate_hash);
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
  globalThis.fetch = async (url) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/exchange")) return Response.json({ protocol_version: PROTOCOL_VERSION, capability });
    if (path.endsWith("/context")) return Response.json(context);
    if (path.endsWith("/preview")) {
      return Response.json({ detail: "The tailoring context changed; start a new session" }, { status: 409 });
    }
    throw new Error(`Unexpected request ${path}`);
  };
  try {
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    await waitForJson(join(evidence, "context.json"), (value) => value.protocol_version === PROTOCOL_VERSION);
    await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "Candidate" }));
    await writeFile(join(output, "RENDER"), "");
    await assert.rejects(resultPromise, /Start a new tailoring session/);
    const status = JSON.parse(await readFile(join(output, "tailoring-status.json"), "utf8"));
    assert.equal(status.state, "context_stale");
    assert.match(status.error, /context changed/);
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
  globalThis.fetch = async (url, options = {}) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/exchange")) return Response.json({ protocol_version: PROTOCOL_VERSION, capability });
    if (path.endsWith("/context")) return Response.json(context);
    if (path.endsWith("/preview")) {
      previewCount += 1;
      if (previewCount > 1) return Response.json({ detail: "The five-candidate-preview resource limit has been reached" }, { status: 409 });
      const candidate = canonicalCandidate(JSON.parse(options.body).candidate);
      const hash = sha(candidate);
      return Response.json({
        candidate,
        format: "pdf",
        pdf_base64: Buffer.from("pdf").toString("base64"),
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
  };
  try {
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    await waitForJson(join(evidence, "context.json"), (value) => value.protocol_version === PROTOCOL_VERSION);
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
  globalThis.fetch = async (url, options = {}) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/exchange")) return Response.json({ protocol_version: PROTOCOL_VERSION, capability });
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
      return Response.json({
        candidate,
        format: "pdf",
        pdf_base64: Buffer.from("pdf").toString("base64"),
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
    await waitForJson(join(evidence, "context.json"), (value) => value.protocol_version === PROTOCOL_VERSION);
    await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "Invalid first attempt" }));
    await writeFile(join(output, "RENDER"), "");
    const validationStatus = await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "candidate_or_preview_error");
    assert.match(validationStatus.error, /candidate\.sections: Field required/);
    assert.doesNotMatch(validationStatus.error, /must-not-be-echoed/);
    await writeFile(join(output, "candidate.json"), JSON.stringify({ title: "Repaired candidate", raw_content: "Complete and valid" }));
    await writeFile(join(output, "RENDER"), "");
    const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.evaluation_id === "evaluation_0123456789abcdef");
    await waitForJson(join(output, "tailoring-status.json"), (value) => value.state === "awaiting_revision_or_selection");
    await writeFile(join(output, "selection.json"), JSON.stringify({
      evaluation_id: preview.evaluation_id,
      candidate_hash: preview.candidate_hash,
    }));
    await writeFile(join(output, "SUBMIT"), "");
    const result = await resultPromise;
    assert.equal(result.status, "draft_ready");
    assert.equal(previewCount, 2);
  } finally {
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
});
