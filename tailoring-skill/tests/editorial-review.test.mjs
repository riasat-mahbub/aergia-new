import test from "node:test";
import assert from "node:assert/strict";

import {
  EDITORIAL_REVIEW_VERSION,
  validateEditorialReview,
  validateInferenceNotes,
} from "../skills/aergia-tailor/scripts/validate-editorial-review.mjs";

const candidateHash = "a".repeat(64);
const candidate = {
  sections: [{ id: "profile", type: "profile", enabled: true, data: { name: "Ada" } }],
};

test("validates an unscored editorial review bound to the rendered candidate", () => {
  const notes = [{ claim: "Jest familiarity", basis: ["unit testing"], confidence: "reasonable", review_recommended: true }];
  const review = validateEditorialReview({
    review_version: EDITORIAL_REVIEW_VERSION,
    candidate_hash: candidateHash,
    pass_number: 1,
    findings: [{
      category: "targeting",
      severity: "polish",
      section_id: "profile",
      excerpt: "Platform engineer",
      problem: "The summary buries the strongest supported target priority.",
      recommended_change: "Bring the best evidence for that priority into the relevant body entry.",
    }],
    inference_notes: notes,
  }, { candidateHash, passNumber: 1, candidate });
  assert.equal(review.review_version, EDITORIAL_REVIEW_VERSION);
  assert.deepEqual(validateInferenceNotes(notes), notes);
});

test("rejects scores, stale hashes, and findings outside the editorial categories", () => {
  const base = {
    review_version: EDITORIAL_REVIEW_VERSION,
    candidate_hash: candidateHash,
    pass_number: 1,
    findings: [],
    inference_notes: [],
  };
  assert.throws(() => validateEditorialReview({ ...base, score: 100 }, { candidateHash, passNumber: 1, candidate }), /unsupported field/);
  assert.throws(() => validateEditorialReview(base, { candidateHash: "b".repeat(64), passNumber: 1, candidate }), /different rendered candidate/);
  assert.throws(() => validateEditorialReview({ ...base, findings: [{ category: "requirement_review", severity: "important", section_id: "profile", excerpt: "x", problem: "x", recommended_change: "x" }] }, { candidateHash, passNumber: 1, candidate }), /category/);
});
