import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { chmod, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  freezeFitReview,
  prepareReviewPackage,
  readFitReviewReport,
  validateFitReviewReport,
} from "../skills/aergia-tailor/scripts/fit-review.mjs";

const evaluationId = "evaluation_0123456789abcdef";
const candidateHash = "a".repeat(64);
const pdfBytes = Buffer.from("exact-pdf-bytes");
const binding = {
  evaluation_id: evaluationId,
  candidate_hash: candidateHash,
  pdf_sha256: createHash("sha256").update(pdfBytes).digest("hex"),
};

function completedReport(overrides = {}) {
  return {
    version: "fit-review-v1",
    ...binding,
    status: "completed",
    mode: "fresh_agent",
    verdict: "generic",
    rationale: "The PDF shows relevant tools but does not connect examples to the role's main responsibilities.",
    strong_connections: ["Visible Python API work"],
    weak_or_missing_connections: ["Production support ownership"],
    recommended_changes: ["Connect the API example to a stated responsibility."],
    ...overrides,
  };
}

test("validates a completed generic report and freezes its nested findings", () => {
  const parsed = validateFitReviewReport(completedReport(), binding);
  const frozen = freezeFitReview(parsed);

  assert.equal(frozen.verdict, "generic");
  assert.equal(Object.isFrozen(frozen), true);
  assert.equal(Object.isFrozen(frozen.strong_connections), true);
  assert.throws(() => frozen.strong_connections.push("changed"), TypeError);
});

test("accepts verdict-free unavailable and explicit-skip reports", () => {
  for (const status of ["unavailable", "skipped_explicitly"]) {
    const report = {
      version: "fit-review-v1",
      ...binding,
      status,
      reason: "A separate reviewer who could inspect the PDF was unavailable.",
    };
    const parsed = validateFitReviewReport(report, binding);
    assert.equal(parsed.status, status);
    assert.equal(Object.hasOwn(parsed, "verdict"), false);
  }
});

test("rejects stale bindings, extra fields, and out-of-contract report bounds", () => {
  assert.throws(() => validateFitReviewReport(completedReport({ candidate_hash: "b".repeat(64) }), binding), /does not match/);
  assert.throws(() => validateFitReviewReport(completedReport({ source_cv_id: "private" }), binding), /unsupported fields/);
  assert.throws(() => validateFitReviewReport(completedReport({ verdict: "unavailable" }), binding), /invalid review verdict/);
  assert.throws(() => validateFitReviewReport(completedReport({ recommended_changes: ["change".repeat(100)] }), binding), /recommended_changes/);
  assert.throws(() => validateFitReviewReport(completedReport({ strong_connections: Array(6).fill("connection") }), binding), /strong_connections/);
});

test("packages exact immutable PDF bytes with only the three allowlisted files and fields", async () => {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-fit-review-package-"));
  try {
    const attempt = {
      evaluationId,
      candidateHash,
      preview: { pdf_sha256: binding.pdf_sha256 },
      pdfBytes,
    };
    const { directory, manifest } = await prepareReviewPackage({
      reviewRoot: workspace,
      attempt,
      job: {
        company: "Example",
        role: "Engineer",
        description: "Build APIs",
        job_url: "https://private.example/job",
        user_instructions: "private instructions",
      },
    });

    assert.deepEqual((await readdir(directory)).sort(), ["candidate.pdf", "job.json", "manifest.json"]);
    assert.deepEqual(await readFile(join(directory, "candidate.pdf")), pdfBytes);
    assert.deepEqual(JSON.parse(await readFile(join(directory, "job.json"), "utf8")), {
      company: "Example",
      role: "Engineer",
      description: "Build APIs",
    });
    assert.deepEqual(manifest, {
      evaluation_id: evaluationId,
      candidate_hash: candidateHash,
      pdf_sha256: binding.pdf_sha256,
    });
    assert.deepEqual(JSON.parse(await readFile(join(directory, "manifest.json"), "utf8")), manifest);
  } finally {
    await rm(workspace, { recursive: true, force: true });
  }
});

test("reads reports with a byte limit and rejects a report for another selected PDF", async () => {
  const workspace = await mkdtemp(join(tmpdir(), "aergia-fit-review-report-"));
  const path = join(workspace, "fit-review.json");
  try {
    assert.equal(await readFitReviewReport(path, binding), null);
    const report = completedReport();
    await writeFile(path, JSON.stringify(report));
    const parsed = await readFitReviewReport(path, binding);
    assert.equal(parsed.evaluation_id, evaluationId);

    await assert.rejects(readFitReviewReport(path, { ...binding, pdf_sha256: "c".repeat(64) }), /does not match/);
    await chmod(path, 0o600);
    await writeFile(path, " ".repeat(65_537));
    await assert.rejects(readFitReviewReport(path, binding), /no larger than 65536 bytes/);
  } finally {
    await rm(workspace, { recursive: true, force: true });
  }
});
