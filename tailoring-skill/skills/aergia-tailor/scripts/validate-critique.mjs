#!/usr/bin/env node

export const CRITIQUE_RUBRIC_VERSION = "aergia-critique-v1";
export const CRITIQUE_PASS_THRESHOLD = 80;
export const MAX_CRITIQUE_PASSES = 5;

export const CRITIQUE_CATEGORY_BUDGETS = Object.freeze({
  job_alignment: 30,
  evidence_credibility: 25,
  impact: 20,
  clarity: 15,
  rendered_presentation: 10,
});

export const CRITIQUE_SEVERITY_DEDUCTIONS = Object.freeze({
  critical: 12,
  important: 5,
  polish: 1,
});

const REQUIREMENT_GAP_DEDUCTIONS = Object.freeze({
  required: 15,
  preferred: 5,
  unknown: 2,
});

const CRITIQUE_KEYS = [
  "rubric_version",
  "candidate_hash",
  "pass_number",
  "seniority_assumption",
  "findings",
  "requirement_review",
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

const REQUIREMENT_REVIEW_KEYS = [
  "requirement_id",
  "status",
  "evidence",
  "rationale",
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function assertObject(value, label) {
  assert(value && typeof value === "object" && !Array.isArray(value), label + " must be an object");
}

function assertOnlyKeys(value, allowed, label) {
  const unexpected = Object.keys(value).filter((key) => !allowed.includes(key));
  assert(unexpected.length === 0, label + " has unsupported field(s): " + unexpected.join(", "));
}

function requiredText(value, label, maximum) {
  assert(typeof value === "string" && value.trim(), label + " must be non-empty text");
  assert(value.trim().length <= maximum, label + " is too long");
  return value.trim();
}

function normalizeImportance(requirement) {
  if (requirement?.importance === "required" || requirement?.required === true) return "required";
  if (requirement?.importance === "unknown") return "unknown";
  if (requirement?.importance === "preferred" || requirement?.required === false) return "preferred";
  return "unknown";
}

function hasId(value, id) {
  if (Array.isArray(value)) return value.some((item) => hasId(item, id));
  if (!value || typeof value !== "object") return false;
  if (value.id === id) return true;
  return Object.values(value).some((item) => hasId(item, id));
}

export function validateCritique(critique, expected = {}) {
  assertObject(critique, "Critique");
  assertOnlyKeys(critique, CRITIQUE_KEYS, "Critique");
  assert(critique.rubric_version === CRITIQUE_RUBRIC_VERSION, "Critique rubric version is unsupported");
  assert(typeof critique.candidate_hash === "string" && /^[0-9a-f]{64}$/.test(critique.candidate_hash), "Critique candidate_hash must be a SHA-256 digest");
  if (expected.candidateHash) {
    assert(critique.candidate_hash === expected.candidateHash, "Critique is for a different rendered candidate");
  }
  assert(Number.isInteger(critique.pass_number) && critique.pass_number >= 1 && critique.pass_number <= MAX_CRITIQUE_PASSES, "Critique pass_number is out of range");
  if (expected.passNumber !== undefined) {
    assert(critique.pass_number === expected.passNumber, "Critique pass_number does not match the latest render");
  }

  const normalized = {
    rubric_version: critique.rubric_version,
    candidate_hash: critique.candidate_hash,
    pass_number: critique.pass_number,
    seniority_assumption: requiredText(critique.seniority_assumption, "seniority_assumption", 200),
    findings: [],
    requirement_review: [],
  };

  const candidate = expected.candidate;
  const sectionIds = new Set(Array.isArray(candidate?.sections) ? candidate.sections.map((section) => section?.id).filter(Boolean) : []);
  assert(Array.isArray(critique.findings) && critique.findings.length <= 50, "Critique findings must be an array of at most 50 items");
  const findingKeys = new Set();
  for (const [index, rawFinding] of critique.findings.entries()) {
    assertObject(rawFinding, "Finding " + (index + 1));
    assertOnlyKeys(rawFinding, FINDING_KEYS, "Finding " + (index + 1));
    assert(Object.hasOwn(CRITIQUE_CATEGORY_BUDGETS, rawFinding.category), "Finding category is unsupported");
    assert(Object.hasOwn(CRITIQUE_SEVERITY_DEDUCTIONS, rawFinding.severity), "Finding severity is unsupported");
    const sectionId = requiredText(rawFinding.section_id, "Finding section_id", 128);
    assert(sectionId === "_document" || sectionIds.has(sectionId), "Finding section_id is not in the candidate");
    const itemId = rawFinding.item_id === undefined ? undefined : requiredText(rawFinding.item_id, "Finding item_id", 128);
    if (itemId !== undefined) {
      const section = candidate?.sections?.find((entry) => entry?.id === sectionId);
      assert(section && hasId(section.data, itemId), "Finding item_id is not in the referenced section");
    }
    const fieldPath = rawFinding.field_path === undefined ? undefined : requiredText(rawFinding.field_path, "Finding field_path", 128);
    const excerpt = requiredText(rawFinding.excerpt, "Finding excerpt", 2_000);
    const problem = requiredText(rawFinding.problem, "Finding problem", 1_000);
    const recommendedChange = requiredText(rawFinding.recommended_change, "Finding recommended_change", 1_000);
    const findingKey = [rawFinding.category, rawFinding.severity, sectionId, itemId ?? "", fieldPath ?? "", excerpt.toLocaleLowerCase(), problem.toLocaleLowerCase()].join("\u0000");
    assert(!findingKeys.has(findingKey), "Critique contains a duplicate finding");
    findingKeys.add(findingKey);
    normalized.findings.push({
      category: rawFinding.category,
      severity: rawFinding.severity,
      section_id: sectionId,
      ...(itemId === undefined ? {} : { item_id: itemId }),
      ...(fieldPath === undefined ? {} : { field_path: fieldPath }),
      excerpt,
      problem,
      recommended_change: recommendedChange,
    });
  }

  const expectedRequirements = Array.isArray(expected.requirements) ? expected.requirements : [];
  assert(expectedRequirements.length <= 100, "Expected requirements exceed the protocol limit");
  assert(Array.isArray(critique.requirement_review) && critique.requirement_review.length === expectedRequirements.length, "Critique must classify every extracted job requirement exactly once");
  const expectedById = new Map();
  for (const requirement of expectedRequirements) {
    assert(typeof requirement?.id === "string" && requirement.id, "Context requirement is missing its id");
    assert(!expectedById.has(requirement.id), "Context contains duplicate requirement ids");
    expectedById.set(requirement.id, requirement);
  }
  const reviewedIds = new Set();
  for (const [index, rawReview] of critique.requirement_review.entries()) {
    assertObject(rawReview, "Requirement review " + (index + 1));
    assertOnlyKeys(rawReview, REQUIREMENT_REVIEW_KEYS, "Requirement review " + (index + 1));
    const requirementId = requiredText(rawReview.requirement_id, "Requirement review requirement_id", 128);
    assert(expectedById.has(requirementId), "Requirement review contains an unknown requirement id");
    assert(!reviewedIds.has(requirementId), "Requirement review contains a duplicate requirement id");
    reviewedIds.add(requirementId);
    assert(["present", "supported_but_missing", "reasonably_inferred", "unsupported"].includes(rawReview.status), "Requirement review status is unsupported");
    normalized.requirement_review.push({
      requirement_id: requirementId,
      status: rawReview.status,
      evidence: requiredText(rawReview.evidence, "Requirement review evidence", 1_000),
      rationale: requiredText(rawReview.rationale, "Requirement review rationale", 1_000),
    });
  }
  assert(reviewedIds.size === expectedById.size, "Critique omitted one or more extracted job requirements");

  return normalized;
}

export function scoreCritique(critique, requirements = []) {
  const deductions = Object.fromEntries(Object.keys(CRITIQUE_CATEGORY_BUDGETS).map((category) => [category, 0]));
  let criticalCount = 0;
  for (const finding of critique.findings) {
    deductions[finding.category] += CRITIQUE_SEVERITY_DEDUCTIONS[finding.severity];
    if (finding.severity === "critical") criticalCount += 1;
  }

  const requirementById = new Map(requirements.map((requirement) => [requirement.id, requirement]));
  let requiredEvidenceGaps = 0;
  for (const review of critique.requirement_review) {
    if (review.status !== "supported_but_missing") continue;
    const importance = normalizeImportance(requirementById.get(review.requirement_id));
    deductions.job_alignment += REQUIREMENT_GAP_DEDUCTIONS[importance];
    if (importance === "required") {
      // A required skill the user can substantiate should be included before
      // the candidate passes. Unsupported JD terms are never penalized here.
      criticalCount += 1;
      requiredEvidenceGaps += 1;
    }
  }

  const categoryScores = {};
  let totalDeduction = 0;
  for (const [category, budget] of Object.entries(CRITIQUE_CATEGORY_BUDGETS)) {
    const applied = Math.min(budget, deductions[category]);
    categoryScores[category] = { available: budget, deduction: applied, score: budget - applied };
    totalDeduction += applied;
  }
  const score = 100 - totalDeduction;
  return {
    score,
    threshold: CRITIQUE_PASS_THRESHOLD,
    passed: score >= CRITIQUE_PASS_THRESHOLD && criticalCount === 0,
    critical_count: criticalCount,
    required_evidence_gaps: requiredEvidenceGaps,
    total_deduction: totalDeduction,
    category_scores: categoryScores,
    unsupported_requirement_count: critique.requirement_review.filter((review) => review.status === "unsupported").length,
    finding_count: critique.findings.length,
  };
}

export function evaluateCritique(critique, expected = {}) {
  const normalized = validateCritique(critique, expected);
  return { ...normalized, ...scoreCritique(normalized, expected.requirements ?? []) };
}
