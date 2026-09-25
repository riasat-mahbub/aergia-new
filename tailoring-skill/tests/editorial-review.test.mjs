import test from "node:test";
import assert from "node:assert/strict";

import {
  EDITORIAL_REVIEW_VERSION,
  validateEditorialReview,
} from "../skills/aergia-tailor/scripts/validate-editorial-review.mjs";

const candidateHash = "a".repeat(64);
const evaluationId = "evaluation_0123456789abcdef";
const candidate = {
  sections: [{ id: "profile", type: "profile", enabled: true, data: { name: "Ada" } }],
};

test("validates an unscored editorial review bound to the rendered candidate", () => {
  const review = validateEditorialReview({
    review_version: EDITORIAL_REVIEW_VERSION,
    evaluation_id: evaluationId,
    candidate_hash: candidateHash,
    findings: [{
      category: "targeting",
      severity: "polish",
      section_id: "profile",
      excerpt: "Platform engineer",
      problem: "The summary buries the strongest supported target priority.",
      recommended_change: "Bring the best evidence for that priority into the relevant body entry.",
    }],
  }, { evaluationId, candidateHash, candidate });
  assert.equal(review.review_version, EDITORIAL_REVIEW_VERSION);
  assert.equal(review.evaluation_id, evaluationId);
});

test("rejects scores, stale hashes, and findings outside the editorial categories", () => {
  const base = {
    review_version: EDITORIAL_REVIEW_VERSION,
    evaluation_id: evaluationId,
    candidate_hash: candidateHash,
    findings: [],
  };
  assert.throws(() => validateEditorialReview({ ...base, score: 100 }, { evaluationId, candidateHash, candidate }), /unsupported field/);
  assert.throws(() => validateEditorialReview(base, { evaluationId: "evaluation_fffffffffffffff", candidateHash, candidate }), /different evaluation/);
  assert.throws(() => validateEditorialReview(base, { evaluationId, candidateHash: "b".repeat(64), candidate }), /different rendered candidate/);
  assert.throws(() => validateEditorialReview({ ...base, findings: [{ category: "requirement_review", severity: "important", section_id: "profile", excerpt: "x", problem: "x", recommended_change: "x" }] }, { evaluationId, candidateHash, candidate }), /category/);
});
