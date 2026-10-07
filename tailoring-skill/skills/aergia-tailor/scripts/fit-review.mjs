import { createHash, randomUUID } from "node:crypto";
import { constants as fsConstants } from "node:fs";
import { chmod, mkdir, open, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const MAX_REPORT_BYTES = 65_536;
const EVALUATION_ID = /^[A-Za-z0-9_-]{16,128}$/;
const SHA256 = /^[0-9a-f]{64}$/;
const COMPLETED_FIELDS = [
  "version",
  "evaluation_id",
  "candidate_hash",
  "pdf_sha256",
  "status",
  "mode",
  "verdict",
  "rationale",
  "strong_connections",
  "weak_or_missing_connections",
  "recommended_changes",
];
const NO_VERDICT_FIELDS = ["version", "evaluation_id", "candidate_hash", "pdf_sha256", "status", "reason"];

function characterLength(value) {
  return Array.from(value).length;
}

function exactKeys(value, expected) {
  const actual = Object.keys(value).sort();
  return actual.length === expected.length && actual.every((key, index) => key === [...expected].sort()[index]);
}

function requireString(value, field, maximum, { nonblank = false } = {}) {
  if (typeof value !== "string" || characterLength(value) < 1 || characterLength(value) > maximum
    || (nonblank && !value.trim())) {
    throw new Error(`fit-review.json has an invalid ${field}`);
  }
}

function requireFindingList(value, field, maximumItems) {
  if (!Array.isArray(value) || value.length > maximumItems) {
    throw new Error(`fit-review.json has an invalid ${field}`);
  }
  for (const item of value) requireString(item, field, 500);
}

export function validateFitReviewReport(value, binding) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("fit-review.json must be an object");
  }
  if (value.version !== "fit-review-v1" || !EVALUATION_ID.test(value.evaluation_id ?? "")
    || !SHA256.test(value.candidate_hash ?? "") || !SHA256.test(value.pdf_sha256 ?? "")) {
    throw new Error("fit-review.json has invalid version or binding fields");
  }
  if (value.evaluation_id !== binding.evaluation_id || value.candidate_hash !== binding.candidate_hash
    || value.pdf_sha256 !== binding.pdf_sha256) {
    throw new Error("fit-review.json does not match the selected preview and exact PDF");
  }

  if (value.status === "completed") {
    if (!exactKeys(value, COMPLETED_FIELDS)) throw new Error("fit-review.json contains unsupported fields");
    if (!["fresh_agent", "manual_external"].includes(value.mode)) {
      throw new Error("fit-review.json has an invalid review mode");
    }
    if (!["tailored", "partially_tailored", "generic"].includes(value.verdict)) {
      throw new Error("fit-review.json has an invalid review verdict");
    }
    requireString(value.rationale, "rationale", 1_200, { nonblank: true });
    requireFindingList(value.strong_connections, "strong_connections", 5);
    requireFindingList(value.weak_or_missing_connections, "weak_or_missing_connections", 5);
    requireFindingList(value.recommended_changes, "recommended_changes", 3);
  } else if (value.status === "unavailable" || value.status === "skipped_explicitly") {
    if (!exactKeys(value, NO_VERDICT_FIELDS)) throw new Error("fit-review.json contains unsupported fields");
    requireString(value.reason, "reason", 500, { nonblank: true });
  } else {
    throw new Error("fit-review.json has an invalid status");
  }
  return structuredClone(value);
}

export async function readFitReviewReport(path, binding) {
  let handle;
  try {
    handle = await open(path, fsConstants.O_RDONLY | fsConstants.O_NOFOLLOW);
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw new Error("fit-review.json could not be read");
  }
  let contents;
  try {
    const before = await handle.stat();
    if (!before.isFile() || before.size < 1 || before.size > MAX_REPORT_BYTES) {
      throw new Error("fit-review.json must be a regular file no larger than 65536 bytes");
    }
    const buffer = Buffer.alloc(MAX_REPORT_BYTES + 1);
    let bytesRead = 0;
    while (bytesRead < buffer.byteLength) {
      const result = await handle.read(buffer, bytesRead, buffer.byteLength - bytesRead, bytesRead);
      if (result.bytesRead === 0) break;
      bytesRead += result.bytesRead;
    }
    const after = await handle.stat();
    if (bytesRead > MAX_REPORT_BYTES || bytesRead !== before.size || !after.isFile()
      || before.dev !== after.dev || before.ino !== after.ino || before.size !== after.size
      || before.mtimeMs !== after.mtimeMs || before.ctimeMs !== after.ctimeMs) {
      throw new Error("fit-review.json changed while it was being read or exceeds 65536 bytes");
    }
    try {
      contents = new TextDecoder("utf-8", { fatal: true }).decode(buffer.subarray(0, bytesRead));
    } catch {
      throw new Error("fit-review.json is not valid UTF-8");
    }
  } finally {
    await handle.close();
  }
  let value;
  try {
    value = JSON.parse(contents);
  } catch {
    throw new Error("fit-review.json is not valid JSON");
  }
  return validateFitReviewReport(value, binding);
}

export async function prepareReviewPackage({ reviewRoot, attempt, job }) {
  const pdfBytes = attempt?.pdfBytes;
  if (!Buffer.isBuffer(pdfBytes) || pdfBytes.length === 0) throw new Error("The selected preview PDF is unavailable in memory");
  const digest = createHash("sha256").update(pdfBytes).digest("hex");
  if (digest !== attempt.preview.pdf_sha256) throw new Error("The selected preview PDF does not match its saved digest");

  const directory = resolve(reviewRoot, `review-package-${randomUUID()}`);
  await mkdir(directory, { recursive: false, mode: 0o700 });
  const reviewJob = Object.fromEntries(["company", "role", "description"]
    .filter((field) => Object.hasOwn(job, field))
    .map((field) => [field, job[field]]));
  const manifest = {
    evaluation_id: attempt.evaluationId,
    candidate_hash: attempt.candidateHash,
    pdf_sha256: attempt.preview.pdf_sha256,
  };
  const files = [
    ["candidate.pdf", pdfBytes],
    ["job.json", Buffer.from(`${JSON.stringify(reviewJob, null, 2)}\n`, "utf8")],
    ["manifest.json", Buffer.from(`${JSON.stringify(manifest, null, 2)}\n`, "utf8")],
  ];
  for (const [name, contents] of files) {
    const path = resolve(directory, name);
    await writeFile(path, contents, { flag: "wx", mode: 0o600 });
    await chmod(path, 0o400);
  }
  return { directory, manifest };
}

export function freezeFitReview(value) {
  if (!value || typeof value !== "object") return value;
  for (const child of Object.values(value)) freezeFitReview(child);
  return Object.freeze(value);
}
