import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { runSession, serverOriginFromSessionUrl } from "../skills/aergia-tailor/scripts/session.mjs";

test("session helper accepts only scoped Aergia session links", () => {
  assert.equal(serverOriginFromSessionUrl("https://aergia.example/agent/tailor/session-1"), "https://aergia.example");
  assert.throws(() => serverOriginFromSessionUrl("https://aergia.example/applications"), /not an Aergia tailoring session/);
  assert.throws(() => serverOriginFromSessionUrl("javascript:alert(1)"), /safe HTTP\(S\)/);
});

test("session helper uses v2 context and keeps capability out of files", async () => {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-tailor-session-"));
  const context = {
    protocol_version: 2,
    session_id: "session-1",
    application_id: "application-1",
    source_cv_id: null,
    expires_at: new Date(Date.now() + 60_000).toISOString(),
    context_hash: "a".repeat(64),
    job: { company: "Example", role: "Engineer", description: "Build APIs" },
    profile: { name: "Ada" },
    previous_cv: null,
    library: [],
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
  const calls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url: String(url), options });
    if (String(url).endsWith("/exchange")) return Response.json({ protocol_version: 2, capability: "scoped-capability" });
    if (String(url).endsWith("/context")) return Response.json(context);
    return Response.json({ protocol_version: 2, status: "draft_ready", draft_cv_id: "draft-1", candidate_hash: "c".repeat(64), relevance: {}, warnings: [] });
  };
  try {
    const output = join(workspace, "output");
    const source = join(workspace, "source");
    await import("node:fs/promises").then(({ mkdir }) => mkdir(output, { recursive: true }));
    await import("node:fs/promises").then(({ mkdir }) => mkdir(source, { recursive: true }));
    await writeFile(join(output, "candidate.json"), JSON.stringify(candidate));
    await writeFile(join(output, "SUBMIT"), "");
    const result = await runSession("https://aergia.example/agent/tailor/session-1", workspace, { code: "code-1234567890123456" });
    assert.equal(result.status, "draft_ready");
    assert.equal(calls.length, 3);
    assert.equal(calls[1].options.headers["X-Aergia-Tailoring-Capability"], "scoped-capability");
    assert.equal(calls[2].options.headers["X-Aergia-Tailoring-Capability"], "scoped-capability");
    assert.doesNotMatch(await readFile(join(output, "result.json"), "utf8"), /scoped-capability/);
    assert.doesNotMatch(await readFile(join(source, "context.json"), "utf8"), /scoped-capability/);
  } finally {
    globalThis.fetch = originalFetch;
    await rm(workspace, { recursive: true, force: true });
  }
});
