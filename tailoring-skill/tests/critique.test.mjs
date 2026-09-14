import test from "node:test";
import assert from "node:assert/strict";

import {
  CRITIQUE_PASS_THRESHOLD,
  evaluateCritique,
} from "../skills/aergia-tailor/scripts/validate-critique.mjs";

const candidateHash = "a".repeat(64);
const requirements = [
  { id: "req-python", required: true, importance: "required" },
  { id: "req-cloud", required: false, importance: "preferred" },
];
const candidate = {
  sections: [{ id: "experience", data: [{ id: "role-1", description: "Built a Python API" }] }],
};

function critique(overrides = {}) {
  return {
    rubric_version: "aergia-critique-v1",
    candidate_hash: candidateHash,
    pass_number: 1,
    seniority_assumption: "mid-level individual contributor",
    findings: [],
    requirement_review: [
      { requirement_id: "req-python", status: "present", evidence: "Experience says Python API", rationale: "Directly represented." },
      { requirement_id: "req-cloud", status: "unsupported", evidence: "No cloud experience in the supplied material", rationale: "Leave the gap honest." },
    ],
    ...overrides,
  };
}

test("a fully covered critique passes with the controller-calculated maximum score", () => {
  const result = evaluateCritique(critique(), { candidateHash, passNumber: 1, candidate, requirements });

  assert.equal(result.score, 100);
  assert.equal(result.threshold, CRITIQUE_PASS_THRESHOLD);
  assert.equal(result.passed, true);
  assert.equal(result.critical_count, 0);
  assert.equal(result.unsupported_requirement_count, 1);
});

test("controller deductions are capped per category and Critical findings always fail", () => {
  const result = evaluateCritique(critique({
    findings: [
      { category: "impact", severity: "critical", section_id: "experience", item_id: "role-1", excerpt: "Built a Python API", problem: "The claim is unsupported by the supplied evidence.", recommended_change: "Remove or accurately qualify the claim." },
      { category: "impact", severity: "important", section_id: "experience", item_id: "role-1", excerpt: "Built a Python API", problem: "The result is not clear.", recommended_change: "State the supported outcome." },
      { category: "impact", severity: "polish", section_id: "experience", item_id: "role-1", excerpt: "Built a Python API", problem: "The sentence could be tighter.", recommended_change: "Remove redundant wording." },
    ],
  }), { candidateHash, passNumber: 1, candidate, requirements });

  assert.equal(result.category_scores.impact.deduction, 18);
  assert.equal(result.score, 82);
  assert.equal(result.critical_count, 1);
  assert.equal(result.passed, false);
});

test("a supported but omitted required skill creates an automatic Critical gap", () => {
  const result = evaluateCritique(critique({
    requirement_review: [
      { requirement_id: "req-python", status: "supported_but_missing", evidence: "The Library project row documents Python API work.", rationale: "Strong relevant evidence exists but is absent from the candidate." },
      { requirement_id: "req-cloud", status: "unsupported", evidence: "No cloud evidence was supplied.", rationale: "Do not add the keyword." },
    ],
  }), { candidateHash, passNumber: 1, candidate, requirements });

  assert.equal(result.category_scores.job_alignment.deduction, 15);
  assert.equal(result.required_evidence_gaps, 1);
  assert.equal(result.critical_count, 1);
  assert.equal(result.passed, false);
});

test("stale hashes, unreviewed requirements, invented scores, and invalid locations are rejected", () => {
  assert.throws(() => evaluateCritique(critique(), { candidateHash: "b".repeat(64), passNumber: 1, candidate, requirements }), /different rendered candidate/);
  assert.throws(() => evaluateCritique(critique(), { candidateHash, passNumber: 2, candidate, requirements }), /pass_number/);
  assert.throws(() => evaluateCritique(critique({ score: 100 }), { candidateHash, passNumber: 1, candidate, requirements }), /unsupported field/);
  assert.throws(() => evaluateCritique(critique({ requirement_review: [] }), { candidateHash, passNumber: 1, candidate, requirements }), /every extracted job requirement/);
  assert.throws(() => evaluateCritique(critique({
    findings: [{ category: "clarity", severity: "important", section_id: "missing", excerpt: "line", problem: "Problem", recommended_change: "Change it." }],
  }), { candidateHash, passNumber: 1, candidate, requirements }), /section_id/);
});
