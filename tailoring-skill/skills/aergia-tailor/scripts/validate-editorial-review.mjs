#!/usr/bin/env node

export const EDITORIAL_REVIEW_VERSION = "aergia-editorial-review-v1";
export const MAX_EVALUATED_PASSES = 5;

const REVIEW_KEYS = [
  "review_version",
  "candidate_hash",
  "pass_number",
  "findings",
  "inference_notes",
];

const FINDING_KEYS = [
  "category",
  "severity",
  "section_id",
  "item_id",
  "field_path",
  "excerpt",
  "problem",
  "recommended_change",
];

const INFERENCE_KEYS = [
  "claim",
  "basis",
  "confidence",
  "section_id",
  "item_id",
  "field_path",
  "review_recommended",
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function assertObject(value, label) {
  assert(value && typeof value === "object" && !Array.isArray(value), `${label} must be an object`);
}

function assertOnlyKeys(value, allowed, label) {
  const unexpected = Object.keys(value).filter((key) => !allowed.includes(key));
  assert(unexpected.length === 0, `${label} has unsupported field(s): ${unexpected.join(", ")}`);
}

function text(value, label, maximum) {
  assert(typeof value === "string" && value.trim(), `${label} must be non-empty text`);
  assert(value.trim().length <= maximum, `${label} is too long`);
  return value.trim();
}

function optionalText(value, label, maximum) {
  if (value === undefined || value === null) return undefined;
  return text(value, label, maximum);
}

function hasId(value, id) {
  if (Array.isArray(value)) return value.some((item) => hasId(item, id));
  if (!value || typeof value !== "object") return false;
  if (value.id === id) return true;
  return Object.values(value).some((item) => hasId(item, id));
}

export function validateInferenceNotes(notes) {
  assert(Array.isArray(notes), "Inference notes must be an array");
  assert(notes.length <= 20, "Inference notes must contain at most 20 items");
  return notes.map((raw, index) => {
    assertObject(raw, `Inference note ${index + 1}`);
    assertOnlyKeys(raw, INFERENCE_KEYS, `Inference note ${index + 1}`);
    assert(Array.isArray(raw.basis) && raw.basis.length >= 1 && raw.basis.length <= 8, `Inference note ${index + 1} basis must contain 1–8 items`);
    const basis = raw.basis.map((item, basisIndex) => text(item, `Inference note ${index + 1} basis ${basisIndex + 1}`, 500));
    assert(["entailed", "strong", "reasonable", "speculative"].includes(raw.confidence), `Inference note ${index + 1} confidence is unsupported`);
    if (raw.review_recommended !== undefined) assert(typeof raw.review_recommended === "boolean", `Inference note ${index + 1} review_recommended must be boolean`);
    return {
      claim: text(raw.claim, `Inference note ${index + 1} claim`, 500),
      basis,
      confidence: raw.confidence,
      ...(optionalText(raw.section_id, `Inference note ${index + 1} section_id`, 128) ? { section_id: raw.section_id.trim() } : {}),
      ...(optionalText(raw.item_id, `Inference note ${index + 1} item_id`, 128) ? { item_id: raw.item_id.trim() } : {}),
      ...(optionalText(raw.field_path, `Inference note ${index + 1} field_path`, 256) ? { field_path: raw.field_path.trim() } : {}),
      review_recommended: raw.review_recommended ?? true,
    };
  });
}

export function validateEditorialReview(review, expected = {}) {
  assertObject(review, "Editorial review");
  assertOnlyKeys(review, REVIEW_KEYS, "Editorial review");
  assert(review.review_version === EDITORIAL_REVIEW_VERSION, "Editorial review version is unsupported");
  assert(typeof review.candidate_hash === "string" && /^[0-9a-f]{64}$/.test(review.candidate_hash), "Editorial review candidate_hash must be a SHA-256 digest");
  if (expected.candidateHash) assert(review.candidate_hash === expected.candidateHash, "Editorial review is for a different rendered candidate");
  assert(Number.isInteger(review.pass_number) && review.pass_number >= 1 && review.pass_number <= MAX_EVALUATED_PASSES, "Editorial review pass_number is out of range");
  if (expected.passNumber !== undefined) assert(review.pass_number === expected.passNumber, "Editorial review pass_number does not match the latest render");

  const candidate = expected.candidate;
  const sectionIds = new Set(Array.isArray(candidate?.sections) ? candidate.sections.map((section) => section?.id).filter(Boolean) : []);
  assert(Array.isArray(review.findings) && review.findings.length <= 50, "Editorial review findings must be an array of at most 50 items");
  const findings = [];
  const findingKeys = new Set();
  for (const [index, raw] of review.findings.entries()) {
    assertObject(raw, `Editorial finding ${index + 1}`);
    assertOnlyKeys(raw, FINDING_KEYS, `Editorial finding ${index + 1}`);
    assert(["evidence_selection", "targeting", "framing", "impact", "clarity", "natural_writing", "visual_balance"].includes(raw.category), `Editorial finding ${index + 1} category is unsupported`);
    assert(["important", "polish", "blocking"].includes(raw.severity), `Editorial finding ${index + 1} severity is unsupported`);
    const sectionId = text(raw.section_id, `Editorial finding ${index + 1} section_id`, 128);
    assert(sectionId === "_document" || sectionIds.has(sectionId), `Editorial finding ${index + 1} section_id is not in the candidate`);
    const itemId = optionalText(raw.item_id, `Editorial finding ${index + 1} item_id`, 128);
    if (itemId !== undefined) {
      const section = candidate?.sections?.find((entry) => entry?.id === sectionId);
      assert(section && hasId(section.data, itemId), `Editorial finding ${index + 1} item_id is not in the referenced section`);
    }
    const fieldPath = optionalText(raw.field_path, `Editorial finding ${index + 1} field_path`, 256);
    const excerpt = text(raw.excerpt, `Editorial finding ${index + 1} excerpt`, 2_000);
    const problem = text(raw.problem, `Editorial finding ${index + 1} problem`, 1_000);
    const recommendedChange = text(raw.recommended_change, `Editorial finding ${index + 1} recommended_change`, 1_000);
    const key = [raw.category, raw.severity, sectionId, itemId ?? "", fieldPath ?? "", excerpt.toLocaleLowerCase(), problem.toLocaleLowerCase()].join("\u0000");
    assert(!findingKeys.has(key), `Editorial review contains a duplicate finding`);
    findingKeys.add(key);
    findings.push({
      category: raw.category,
      severity: raw.severity,
      section_id: sectionId,
      ...(itemId === undefined ? {} : { item_id: itemId }),
      ...(fieldPath === undefined ? {} : { field_path: fieldPath }),
      excerpt,
      problem,
      recommended_change: recommendedChange,
    });
  }

  return {
    review_version: EDITORIAL_REVIEW_VERSION,
    candidate_hash: review.candidate_hash,
    pass_number: review.pass_number,
    findings,
    inference_notes: validateInferenceNotes(review.inference_notes ?? []),
  };
}
