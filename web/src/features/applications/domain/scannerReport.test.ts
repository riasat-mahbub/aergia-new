import assert from "node:assert/strict";
import test from "node:test";
import type { Application, ScanResult, ScannerExpressionEvaluation, ScannerExpressionNode, ScannerRequirement } from "../types/index.ts";
import { buildScannerReportViewModel, scannerBadgeState } from "./scannerReport.ts";

const location = (fieldPath: string, excerpt: string) => ({
  section_id: "experience",
  section_type: "experience",
  entry_id: "entry-1",
  field_path: fieldPath,
  excerpt,
});

function leaf(id: string, name: string, expectation = "familiarity"): ScannerExpressionNode {
  return {
    kind: "leaf",
    id,
    concept: { name, family: "hard_skill", source_text: name },
    expectation: { kind: expectation, qualifier: null },
    modifiers: { optional: false, list_semantics: "single", scope: null },
  };
}

function evaluation(node: ScannerExpressionNode, status: ScannerExpressionEvaluation["status"], children: ScannerExpressionEvaluation[] = [], evidenceIds: string[] = []): ScannerExpressionEvaluation {
  return {
    node_id: node.id,
    status,
    optional: node.modifiers?.optional ?? false,
    mandatory_total: children.length || 1,
    mandatory_supported: children.filter((child) => child.status === "supported").length,
    evidence_ids: evidenceIds,
    children,
  };
}

const allRequirement: ScannerRequirement = {
  id: "req-all",
  source: {
    original_text: "Experience with Python and Docker",
    source_start: 0,
    source_end: 36,
    section: { title: "Qualifications", purpose: "candidate_qualifications", confidence: 0.98 },
  },
  importance: "required",
  family: "hard_skill",
  weight: 1,
  expression: {
    kind: "all",
    id: "all-root",
    children: [leaf("python", "Python"), leaf("docker", "Docker")],
  },
  contextual_modifiers: [],
};

const examplesRequirement: ScannerRequirement = {
  id: "req-examples",
  source: {
    original_text: "Participate in team rituals such as standups and demos",
    source_start: 40,
    source_end: 96,
    section: { title: "Responsibilities", purpose: "candidate_responsibilities", confidence: 0.97 },
  },
  importance: "required",
  family: "responsibility",
  weight: 1,
  expression: {
    kind: "examples",
    id: "examples-root",
    subject: leaf("rituals", "Team rituals", "participation"),
    examples: [leaf("standups", "Standups"), leaf("demos", "Demos")],
    min_supporting_examples: 0,
  },
  contextual_modifiers: [],
};

function makeResult(): ScanResult {
  const python = leaf("python", "Python");
  const docker = leaf("docker", "Docker");
  const rituals = leaf("rituals", "Team rituals", "participation");
  const standups = leaf("standups", "Standups");
  const demos = leaf("demos", "Demos");
  const allEvaluation = evaluation(
    allRequirement.expression,
    "partial",
    [evaluation(python, "supported", [], ["e-python"]), evaluation(docker, "not_evidenced")],
  );
  const examplesEvaluation = evaluation(
    examplesRequirement.expression,
    "not_evidenced",
    [evaluation(rituals, "not_evidenced"), evaluation(standups, "not_evidenced"), evaluation(demos, "not_evidenced")],
  );
  return {
    schema_version: "scanner-v1",
    created_at: "2026-09-21T00:00:00Z",
    input_fingerprints: { job_description_sha256: "job", cv_content_sha256: "cv", pdf_sha256: null },
    versions: { extractor_version: "extractor", matcher_version: "matcher", lexical_version: "lexical", quality_version: "quality", pdf_analysis_version: "pdf" },
    requirement_extraction: { status: "evaluated", requirements: [allRequirement, examplesRequirement], warnings: ["concept_spans_not_promoted:1"] },
    semantic: {
      status: "evaluated",
      requirements: [
        { requirement_id: allRequirement.id, status: "partial", expression: allEvaluation },
        { requirement_id: examplesRequirement.id, status: "not_evidenced", expression: examplesEvaluation },
      ],
      evidence: [{ id: "e-python", locations: [location("experience[0].description", "Built Python services")], concept_status: "supported", expectation_status: "supported", confidence: 0.95, method: "exact" }],
      summary: {
        status: "available",
        job_fit: 0.51,
        scorable_fraction: 1,
        classified_fraction: 1,
        evidence_scorable_fraction: 1,
        classification_warning_code: null,
        qualification_fit: { score: 0.5, scorable_fraction: 1, scorable_weight: 1, total_weight: 1, requirement_count: 1 },
        responsibility_alignment: { score: 0, scorable_fraction: 1, scorable_weight: 1, total_weight: 1, requirement_count: 1 },
        preferred_fit: { score: null, scorable_fraction: 0, scorable_weight: 0, total_weight: 0, requirement_count: 0 },
        unclassified_requirement_count: 0,
        supported_requirement_count: 0,
        partial_requirement_count: 1,
        not_evidenced_requirement_count: 1,
        conflicting_requirement_count: 0,
        unverifiable_requirement_count: 0,
        unverifiable_component_count: 0,
        supported_count: 0,
        partial_count: 1,
        not_evidenced_count: 1,
        conflicting_count: 0,
        unverifiable_count: 0,
        required_constraint_conflicts: 0,
      },
    },
    lexical: {
      status: "evaluated",
      terms: [
        { id: "term-python", term: "Python", canonical_concept_id: "python", variants: [], importance: "required", source_locations: [], illustrative_example: false, visibility: "exact", evidence: [{ location: location("skills", "Python"), matched_text: "Python", visibility: "exact" }], semantic_support: "supported" },
        { id: "term-docker", term: "Docker", canonical_concept_id: "docker", variants: [], importance: "required", source_locations: [], illustrative_example: false, visibility: "absent", evidence: [], semantic_support: "supported" },
        { id: "term-standups", term: "Standups", canonical_concept_id: "standups", variants: [], importance: "required", source_locations: [{ source_start: 75, source_end: 83, section_title: "Responsibilities", section_purpose: "candidate_responsibilities", importance: "required", illustrative_example: true }], illustrative_example: true, visibility: "absent", evidence: [], semantic_support: "not_evidenced" },
      ],
      summary: { status: "available", visibility_score: 0.5, scorable_fraction: 1, exact_count: 1, normalized_count: 0, variant_count: 0, absent_count: 2, unverifiable_count: 0 },
    },
    presentation_quality: { status: "evaluated", findings: [], bullet_assessments: [] },
    pdf_recovery: { status: "unavailable", page_count: null, checks: [], summary: null },
  } as ScanResult;
}

function application(result: ScanResult | null, scannerStatus: Application["scanner_status"] = result ? "current" : "not_scanned"): Application {
  return {
    id: "application-1",
    cv_id: "cv-1",
    company: "Example Co",
    role: "Engineer",
    job_url: null,
    job_description: "A job",
    notes: null,
    status: "draft",
    applied_at: null,
    extracted_keywords: [],
    relevance: {},
    algorithm_version: "legacy",
    created_at: "2026-09-21T00:00:00Z",
    updated_at: "2026-09-21T00:00:00Z",
    scanner_result: result,
    scanner_status: scannerStatus,
  };
}

test("builds a user-facing report without exposing expression node kinds", () => {
  const report = buildScannerReportViewModel(makeResult(), application(makeResult()));
  assert.equal(report.score.jobFit, 0.51);
  assert.equal(report.score.partialCount, 1);
  assert.equal(report.requirements[0]?.components.map((item) => item.title).join(", "), "Python, Docker");
  assert.equal(report.requirements[1]?.components.find((item) => item.title === "Standups")?.illustrative, true);
  assert.equal(report.keywords.safeWording[0]?.term, "Docker");
  assert.equal(report.keywords.employerVocabulary[0]?.term, "Standups");
  assert.equal(report.diagnostics.extractionWarnings[0], "concept_spans_not_promoted:1");
});

test("keeps badge states explicit for current, stale, and not-scanned applications", () => {
  const result = makeResult();
  assert.equal(scannerBadgeState(application(result)).label, "Job Fit 51%");
  assert.match(scannerBadgeState(application(result, "stale")).label, /Update needed/);
  assert.equal(scannerBadgeState(application(null)).label, "Analyze CV");
});

test("maps ATS guidance into explainable common and platform findings", () => {
  const result = makeResult();
  result.ats_guidance = {
    schema_version: "ats-guidance-v1",
    version: "ats-guidance-v1",
    common_findings: [{
      id: "heading-experience",
      rule_id: "conventional_section_headings",
      title: "Conventional section heading",
      category: "headings",
      scope: "common",
      severity: "warning",
      explanation: "Use a conventional label.",
      action: "Review the heading.",
      affected_items: ["What I did"],
      recovered_items: [],
      missing_items: [],
      applies_to: [],
      source_ids: [],
    }],
    platform_sensitive_findings: [],
    platforms: {
      workday: { id: "workday", name: "Workday", findings: [], tips: [], source_ids: [] },
    },
    heading_conventions: [],
    date_compatibility: [],
    acronym_coverage: [],
    entry_completeness: [],
    summary: { platforms_checked: 14, common_pass_count: 1, common_warning_count: 1, recommendation_count: 0, informational_count: 0 },
  };
  const report = buildScannerReportViewModel(result, application(result));

  assert.equal(report.ats.guidance.available, true);
  assert.equal(report.ats.guidance.commonFindings[0]?.severityLabel, "Needs attention");
  assert.equal(report.ats.guidance.commonFindings[0]?.affected_items[0], "What I did");
  assert.equal(report.ats.guidance.summary?.platforms_checked, 14);
});
