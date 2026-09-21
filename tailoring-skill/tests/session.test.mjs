import test from "node:test";
import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { runSession, serverOriginFromSessionUrl } from "../skills/aergia-tailor/scripts/session.mjs";

const emptyCritique = (candidateHash, passNumber) => ({
  rubric_version: "aergia-critique-v1",
  candidate_hash: candidateHash,
  pass_number: passNumber,
  seniority_assumption: "individual contributor",
  findings: [],
  requirement_review: [],
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
    protocol_version: 4,
    session_id: "session-1",
    application_id: "application-1",
    source_cv_id: null,
    // Keep a failed helper from keeping the test worker alive for a full
    // production-length session timeout.
    expires_at: new Date(Date.now() + 20_000).toISOString(),
    context_hash: "a".repeat(64),
    job: { company: "Example", role: "Engineer", description: "Build APIs" },
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

function mockTailoringServer(context) {
  const calls = [];
  let previewNumber = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url: String(url), options });
    if (String(url).endsWith("/exchange")) return Response.json({ protocol_version: 4, capability: "scoped-capability" });
    if (String(url).endsWith("/context")) return Response.json(context);
    if (String(url).endsWith("/preview")) {
      previewNumber += 1;
      return Response.json({
        format: "pdf",
        pdf_base64: Buffer.from("pdf-" + previewNumber).toString("base64"),
        page_count: 1,
        candidate_hash: String(previewNumber).padStart(64, "0"),
        scanner_result: { schema_version: "scanner-v1", semantic: { summary: { job_fit: 0.95 } } },
        render_warnings: [],
      });
    }
    const submitBody = JSON.parse(options.body);
    return Response.json({ protocol_version: 4, status: "draft_ready", draft_cv_id: "draft-1", candidate_hash: submitBody.expected_candidate_hash, scanner_result: {}, render_warnings: [] });
  };
  return { calls, restore: () => { globalThis.fetch = originalFetch; } };
}

test("session helper accepts only scoped Aergia session links", () => {
  assert.equal(serverOriginFromSessionUrl("https://aergia.example/agent/tailor/session-1"), "https://aergia.example");
  assert.throws(() => serverOriginFromSessionUrl("https://aergia.example/applications"), /not an Aergia tailoring session/);
  assert.throws(() => serverOriginFromSessionUrl("javascript:alert(1)"), /safe HTTP\(S\)/);
});

test("session helper requires an exact passing rendered critique and keeps capability out of files", async () => {
  const { workspace, output, context, candidate } = await makeSessionWorkspace();
  const server = mockTailoringServer(context);
  try {
    const source = join(workspace, "source");
    await mkdir(source, { recursive: true });
    await writeFile(join(output, "review-notes.json"), JSON.stringify(["Zustand use inferred from the inspected project source."]));
    await writeFile(join(output, "RENDER"), "");
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.pass_number === 1);
    assert.equal(preview.scanner_result.semantic.summary.job_fit, 0.95);
    await writeFile(join(output, "critique.json"), JSON.stringify(emptyCritique(preview.candidate_hash, 1)));
    await writeFile(join(output, "CRITIQUE"), "");
    const assessment = await waitForJson(join(output, "critique-result.json"), (value) => value.pass_number === 1 && value.valid === true);
    assert.equal(assessment.score, 100);
    assert.equal(assessment.passed, true);

    await writeFile(join(output, "candidate.json"), JSON.stringify({ ...candidate, title: "Edited after preview" }));
    await writeFile(join(output, "SUBMIT"), "");
    const rejected = await waitForJson(join(output, "critique-status.json"), (value) => value.state === "submit_rejected");
    assert.match(rejected.error, /No passing critique/);
    assert.equal(server.calls.filter((call) => call.url.endsWith("/submit")).length, 0);

    await writeFile(join(output, "candidate.json"), JSON.stringify(candidate));
    await writeFile(join(output, "SUBMIT"), "");
    const result = await resultPromise;
    assert.equal(result.status, "draft_ready");
    assert.equal(server.calls.length, 4);
    assert.equal(server.calls[1].options.headers["X-Aergia-Tailoring-Capability"], "scoped-capability");
    assert.equal(server.calls[2].options.headers["X-Aergia-Tailoring-Capability"], "scoped-capability");
    assert.equal(server.calls[3].options.headers["X-Aergia-Tailoring-Capability"], "scoped-capability");
    assert.deepEqual(JSON.parse(server.calls[3].options.body).review_notes, ["Zustand use inferred from the inspected project source."]);
    assert.doesNotMatch(await readFile(join(output, "result.json"), "utf8"), /scoped-capability/);
    assert.doesNotMatch(await readFile(join(source, "context.json"), "utf8"), /scoped-capability/);
  } finally {
    server.restore();
    await rm(workspace, { recursive: true, force: true });
  }
});

test("five failing critiques fall back to the best reviewed candidate with a user note", async () => {
  const { workspace, output, context, candidate } = await makeSessionWorkspace();
  const server = mockTailoringServer(context);
  try {
    await writeFile(join(output, "RENDER"), "");
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    let bestTitle = null;
    for (let pass = 1; pass <= 5; pass += 1) {
      const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.pass_number === pass);
      const findingCount = [3, 2, 1, 2, 1][pass - 1];
      const findings = Array.from({ length: findingCount }, (_, index) => ({
        category: "evidence_credibility",
        severity: "critical",
        section_id: "profile",
        excerpt: "Ada",
        problem: "Unsupported claim " + (index + 1),
        recommended_change: "Remove the unsupported claim.",
      }));
      const critique = { ...emptyCritique(preview.candidate_hash, pass), findings };
      await writeFile(join(output, "critique.json"), JSON.stringify(critique));
      await writeFile(join(output, "CRITIQUE"), "");
      const assessment = await waitForJson(join(output, "critique-result.json"), (value) => value.pass_number === pass && value.valid === true);
      assert.equal(assessment.passed, false);
      if (pass === 3) bestTitle = "Candidate pass 3";
      if (pass < 5) {
        await writeFile(join(output, "candidate.json"), JSON.stringify({ ...candidate, title: "Candidate pass " + (pass + 1) }));
        await writeFile(join(output, "RENDER"), "");
      }
    }

    const state = await waitForJson(join(output, "critique-status.json"), (value) => value.state === "fallback_available");
    assert.equal(state.pass_number, 5);
    assert.equal(JSON.parse(await readFile(join(output, "best-candidate.json"), "utf8")).title, bestTitle);
    await writeFile(join(output, "SUBMIT"), "");
    await resultPromise;

    const submitCall = server.calls.find((call) => call.url.endsWith("/submit"));
    assert.ok(submitCall);
    const body = JSON.parse(submitCall.options.body);
    assert.equal(body.candidate.title, bestTitle);
    assert.ok(body.review_notes.some((note) => /threshold 80/.test(note)));
    assert.equal(server.calls.filter((call) => call.url.endsWith("/preview")).length, 5);
  } finally {
    server.restore();
    await rm(workspace, { recursive: true, force: true });
  }
});

test("repeated candidates stop early and cannot trigger another preview", async () => {
  const { workspace, output, context, candidate } = await makeSessionWorkspace();
  const server = mockTailoringServer(context);
  try {
    await writeFile(join(output, "RENDER"), "");
    const resultPromise = runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    void resultPromise.catch(() => undefined);
    for (let pass = 1; pass <= 2; pass += 1) {
      const preview = await waitForJson(join(output, "candidate-preview.json"), (value) => value.pass_number === pass);
      const critique = {
        ...emptyCritique(preview.candidate_hash, pass),
        findings: [{
          category: "evidence_credibility",
          severity: "critical",
          section_id: "profile",
          excerpt: "Ada",
          problem: "Unsupported claim",
          recommended_change: "Remove the unsupported claim.",
        }],
      };
      await writeFile(join(output, "critique.json"), JSON.stringify(critique));
      await writeFile(join(output, "CRITIQUE"), "");
      const assessment = await waitForJson(join(output, "critique-result.json"), (value) => value.pass_number === pass && value.valid === true);
      assert.equal(assessment.passed, false);
      if (pass === 1) await writeFile(join(output, "RENDER"), "");
    }

    const stopped = await waitForJson(join(output, "critique-status.json"), (value) => value.state === "fallback_available");
    assert.equal(stopped.stop_reason, "repeated_candidate");
    await writeFile(join(output, "candidate.json"), JSON.stringify({ ...candidate, title: "Unreviewed third candidate" }));
    await writeFile(join(output, "RENDER"), "");
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
