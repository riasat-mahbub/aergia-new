import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { checkJobDescription } from "../skills/aergia-tailor/scripts/jd-check.mjs";
import { runSession, serverOriginFromSessionUrl } from "../skills/aergia-tailor/scripts/session.mjs";
import { verifyFacts } from "../skills/aergia-tailor/scripts/verify-cv-facts.mjs";

test("session helper accepts only scoped Aergia session links", () => {
  assert.equal(
    serverOriginFromSessionUrl("https://aergia.example/agent/tailor/session-1"),
    "https://aergia.example",
  );
  assert.throws(
    () => serverOriginFromSessionUrl("https://aergia.example/applications"),
    /not an Aergia tailoring session/,
  );
  assert.throws(
    () => serverOriginFromSessionUrl("javascript:alert(1)"),
    /safe HTTP\(S\)/,
  );
});

test("session helper keeps one capability through evidence and submission", async () => {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-session-"));
  const fixtureRoot = new URL("../skills/aergia-tailor/references/fixtures/", import.meta.url);
  const evidence = JSON.parse(await readFile(new URL("evidence-packet.valid.json", fixtureRoot)));
  const patch = JSON.parse(await readFile(new URL("tailoring-patch.valid.json", fixtureRoot)));
  evidence.expires_at = new Date(Date.now() + 60_000).toISOString();
  const calls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url: String(url), options });
    if (String(url).endsWith("/exchange")) {
      return Response.json({ protocol_version: 1, capability: "scoped-capability" });
    }
    if (String(url).endsWith("/evidence")) return Response.json(evidence);
    return Response.json({ protocol_version: 1, status: "applied", applied_operations: ["add_library_entry", "replace_description", "report_gap"] });
  };

  try {
    const output = join(workspace, "output");
    await mkdir(output);
    await writeFile(join(output, "tailoring-patch.json"), JSON.stringify(patch));
    await writeFile(join(output, "SUBMIT"), "");

    const result = await runSession(
      "https://aergia.example/agent/tailor/session-1",
      workspace,
      { code: "code-1234567890123456" },
    );

    assert.equal(result.status, "applied");
    assert.equal(calls.length, 3);
    assert.equal(calls[1].options.headers["X-Aergia-Tailoring-Capability"], "scoped-capability");
    assert.equal(calls[2].options.headers["X-Aergia-Tailoring-Capability"], "scoped-capability");
    assert.doesNotMatch(await readFile(join(output, "result.json"), "utf8"), /scoped-capability/);
  } finally {
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
});

test("JD check separates supported skills from gaps and exposes inconclusive state", () => {
  const result = checkJobDescription(
    { description: "Requirements\nPython and Kubernetes experience required" },
    { sections: [{ data: [{ description: "Built Python services." }] }] },
    [],
  );

  assert.equal(result.inconclusive, false);
  assert.deepEqual(
    result.requirements.map((requirement) => [requirement.requirement, requirement.supportedByResume, requirement.gap]),
    [["kubernetes", false, true], ["python", true, false]],
  );
});

test("JD check uses the server's open-ended requirement set when available", () => {
  const result = checkJobDescription(
    { description: "Experience with Snowflake and stakeholder facilitation." },
    { sections: [{ data: [{ description: "Built Snowflake data pipelines." }] }] },
    [],
    [
      { id: "req-snowflake", text: "Snowflake", normalized: "snowflake", type: "hard_skill", required: true },
      { id: "req-facilitation", text: "Stakeholder facilitation", normalized: "stakeholder facilitation", type: "soft_skill", required: false },
    ],
  );

  assert.deepEqual(
    result.requirements.map((requirement) => [requirement.id, requirement.existing, requirement.gap]),
    [["req-snowflake", true, false], ["req-facilitation", false, true]],
  );
});
test("fact check rejects a new unsupported numeric claim", () => {
  const result = verifyFacts(
    { sections: [{ data: [{ description: "Improved API performance." }] }] },
    { sections: [{ data: [{ description: "Improved API performance by 47%." }] }] },
    { cv: { sections: [{ data: [{ description: "Improved API performance." }] }] }, library: [] },
    { changes: [{ operation: "rewrite_rich_text", evidence: [] }] },
  );

  assert.equal(result.status, "fail");
  assert.equal(result.findings[0].value, "47%");
});

test("fact check does not borrow a number from another CV entry", () => {
  const before = {
    sections: [{
      id: "experience",
      type: "experience",
      data: [
        { id: "job-a", description: "Improved API performance." },
        { id: "job-b", description: "Reduced latency by 32%." },
      ],
    }],
  };
  const after = {
    sections: [{
      id: "experience",
      type: "experience",
      data: [
        { id: "job-a", description: "Improved API performance by 32%." },
        { id: "job-b", description: "Reduced latency by 32%." },
      ],
    }],
  };
  const result = verifyFacts(
    before,
    after,
    { cv: before, library: [] },
    { changes: [{ operation: "replace_description", section_id: "experience", entry_id: "job-a" }] },
  );

  assert.equal(result.status, "fail");
  assert.equal(result.findings[0].value, "32%");
});

test("fact check accepts a new cited claim from a web excerpt", () => {
  const result = verifyFacts(
    { sections: [{ data: [{ description: "Built API services." }] }] },
    { sections: [{ data: [{ description: "Built Python API services with a 47% improvement." }] }] },
    {
      cv: { sections: [{ data: [{ description: "Built API services." }] }] },
      library: [],
    },
    {
      changes: [{
        operation: "replace_rich_text",
        field: "description",
        evidence: [{
          source: "web",
          url: "https://example.com/technical-guide",
          title: "Technical guide",
          excerpt: "Python API services can report a 47% improvement in this contextual example.",
        }],
      }],
    },
  );

  assert.equal(result.status, "pass");
});
