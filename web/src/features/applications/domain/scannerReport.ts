import type {
  Application,
  ScanResult,
  ScannerCVLocation,
  ScannerEvidenceStatus,
  ScannerEvidenceStrength,
  ScannerExpressionEvaluation,
  ScannerExpressionNode,
  ScannerLexicalTerm,
  ScannerAtsFinding,
  ScannerAtsGuidance,
  ScannerRequirement,
  ScannerRequirementEvaluation,
} from "../types";

export type ScannerReportTab = "overview" | "job-fit" | "keywords" | "ats" | "quality" | "pdf";
export type ScannerBadgeState = "current" | "stale" | "needs_rescan" | "not_scanned" | "unavailable";
export type ScannerRequirementFilter = "needs_attention" | "covered" | "all" | "unclassified";
export type ScannerKeywordCategory =
  | "safe_wording"
  | "review_before_adding"
  | "unsupported"
  | "employer_vocabulary"
  | "visible";

export interface ScannerBadgeViewModel {
  state: ScannerBadgeState;
  label: string;
  score: number | null;
  stale: boolean;
  disabled: boolean;
}

export interface ScannerEvidenceViewModel {
  excerpt: string;
  sectionLabel: string;
  location: ScannerCVLocation;
  strength: ScannerEvidenceStrength | null;
}

export interface ScannerComponentViewModel {
  id: string;
  title: string;
  status: ScannerEvidenceStatus;
  optional: boolean;
  illustrative: boolean;
  evidence: ScannerEvidenceViewModel[];
  allEvidence: ScannerEvidenceViewModel[];
}

export interface ScannerRequirementViewModel {
  id: string;
  title: string;
  sourceText: string;
  importance: "required" | "preferred" | "unknown";
  importanceLabel: string;
  status: ScannerEvidenceStatus;
  statusLabel: string;
  bucket: "qualification" | "responsibility" | "preferred" | "unknown";
  components: ScannerComponentViewModel[];
  examples: string[];
  relationLabel: string | null;
  coverageSummary: string;
  classificationLabel: string;
  evidence: ScannerEvidenceViewModel[];
  explanation: string;
  unclassified: boolean;
}

export interface ScannerKeywordViewModel {
  id: string;
  term: string;
  category: ScannerKeywordCategory;
  categoryLabel: string;
  visibility: ScannerLexicalTerm["visibility"];
  visibilityLabel: string;
  semanticSupport: ScannerEvidenceStatus | null;
  occurrenceCount: number;
  evidence: ScannerEvidenceViewModel[];
  allEvidence: ScannerEvidenceViewModel[];
  illustrative: boolean;
  employerVocabulary: boolean;
}

export interface ScannerAtsCheckViewModel {
  code: string;
  label: string;
  status: "pass" | "warning" | "fail" | "unavailable";
  statusLabel: string;
  value: number | null;
  recoveredCount: number | null;
  expectedCount: number | null;
  expectedItems: string[];
  recoveredItems: string[];
  missingItems: string[];
  affectedItems: string[];
  explanation: string;
}

export interface ScannerAtsFindingViewModel extends ScannerAtsFinding {
  severityLabel: string;
  categoryLabel: string;
}

export interface ScannerAtsGuidanceViewModel {
  available: boolean;
  commonFindings: ScannerAtsFindingViewModel[];
  platformSensitiveFindings: ScannerAtsFindingViewModel[];
  platforms: Record<string, {
    id: string;
    name: string;
    findings: ScannerAtsFindingViewModel[];
    tips: ScannerAtsFindingViewModel[];
    source_ids: string[];
  }>;
  headingConventions: NonNullable<ScannerAtsGuidance>["heading_conventions"];
  dateCompatibility: NonNullable<ScannerAtsGuidance>["date_compatibility"];
  acronymCoverage: NonNullable<ScannerAtsGuidance>["acronym_coverage"];
  entryCompleteness: NonNullable<ScannerAtsGuidance>["entry_completeness"];
  summary: NonNullable<ScannerAtsGuidance>["summary"] | null;
}

export interface ScannerQualityFindingViewModel {
  code: string;
  label: string;
  severity: "info" | "warning" | "error";
  severityLabel: string;
  evidence: string | null;
  explanation: string;
  locationLabel: string;
}

export interface ScannerBucketViewModel {
  label: string;
  score: number | null;
  scorableFraction: number;
  totalWeight: number;
  requirementCount: number;
}

export interface ScannerReportViewModel {
  badge: ScannerBadgeViewModel;
  score: {
    status: "available" | "insufficient_scorable_evidence" | "unavailable";
    jobFit: number | null;
    classifiedFraction: number | null;
    evidenceScorableFraction: number | null;
    lowClassificationWarning: boolean;
    coveredCount: number;
    partialCount: number;
    notShownCount: number;
    conflictingCount: number;
    unverifiableCount: number;
    unverifiableComponentCount: number;
    requiredConstraintConflicts: number;
    buckets: {
      qualifications: ScannerBucketViewModel;
      responsibilities: ScannerBucketViewModel;
      preferred: ScannerBucketViewModel;
    };
  };
  requirements: ScannerRequirementViewModel[];
  strengths: ScannerRequirementViewModel[];
  gaps: ScannerRequirementViewModel[];
  keywords: {
    visibilityScore: number | null;
    exactCount: number;
    normalizedCount: number;
    variantCount: number;
    absentCount: number;
    safeWording: ScannerKeywordViewModel[];
    reviewBeforeAdding: ScannerKeywordViewModel[];
    unsupported: ScannerKeywordViewModel[];
    employerVocabulary: ScannerKeywordViewModel[];
    visible: ScannerKeywordViewModel[];
  };
  ats: {
    status: "looks_good" | "needs_attention" | "at_risk" | "unavailable";
    statusLabel: string;
    checks: ScannerAtsCheckViewModel[];
    guidance: ScannerAtsGuidanceViewModel;
  };
  quality: {
    status: "looks_good" | "needs_attention" | "at_risk" | "unavailable";
    statusLabel: string;
    errorCount: number;
    warningCount: number;
    infoCount: number;
    findings: ScannerQualityFindingViewModel[];
    bulletAssessmentCount: number;
  };
  pdf: {
    status: "pass" | "warning" | "fail" | "unavailable";
    statusLabel: string;
    recoveryScore: number | null;
    checks: ScannerAtsCheckViewModel[];
    disclaimer: string;
  };
  diagnostics: {
    versions: ScanResult["versions"];
    extractionWarnings: string[];
    fingerprints: ScanResult["input_fingerprints"];
    raw: ScanResult;
  };
}

const STATUS_LABELS: Record<ScannerEvidenceStatus, string> = {
  supported: "Covered",
  partial: "Partial",
  not_evidenced: "Not shown",
  conflicting: "Conflicting evidence",
  unverifiable: "Couldn’t evaluate",
};

const VISIBILITY_LABELS: Record<ScannerLexicalTerm["visibility"], string> = {
  exact: "Exact wording",
  normalized: "Normalized wording",
  variant: "Surface variant",
  absent: "Not used",
  unverifiable: "Couldn’t evaluate",
};

const CHECK_LABELS: Record<string, string> = {
  text_retention: "Searchable text",
  reading_order: "Reading order",
  contact_recovery: "Contact information",
  section_heading_recovery: "Section structure",
  entry_recovery: "Entry recognition",
  link_recovery: "Links",
};

const ATS_CATEGORY_LABELS: Record<string, string> = {
  parsing: "Parsing",
  headings: "Headings",
  keywords: "Keywords",
  acronyms: "Acronyms",
  dates: "Dates",
  experience: "Experience",
  education: "Education",
  links: "Links",
  application_fields: "Application fields",
};

const STATUS_PRIORITY: Record<ScannerEvidenceStatus, number> = {
  conflicting: 0,
  partial: 1,
  not_evidenced: 2,
  unverifiable: 3,
  supported: 4,
};

const STRENGTH_PRIORITY: Record<ScannerEvidenceStrength, number> = {
  direct_demonstration: 5,
  strong_related_evidence: 4,
  partial_transfer: 3,
  weak_context: 2,
  unsupported: 1,
};

const STRENGTH_LABELS: Record<ScannerEvidenceStrength, string> = {
  direct_demonstration: "Direct demonstration",
  strong_related_evidence: "Strong related evidence",
  partial_transfer: "Partial transfer",
  weak_context: "Weak context",
  unsupported: "Unsupported",
};

function humanize(value: string): string {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function percentage(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${Math.round(value * 100)}%`;
}

function statusLabel(status: ScannerEvidenceStatus): string {
  return STATUS_LABELS[status];
}

function sectionLabel(location: ScannerCVLocation): string {
  return location.section_type ? humanize(location.section_type) : "CV";
}

function locationScore(location: ScannerCVLocation): number {
  const path = location.field_path.toLocaleLowerCase();
  const excerptLength = location.excerpt.trim().length;
  let score = Math.min(excerptLength, 260) / 20;
  if (/bullet|description|summary|content|skill|technology|project/.test(path)) score += 5;
  if (/date|employer|organization|company|location/.test(path)) score -= 5;
  if (location.entry_id) score += 1;
  return score;
}

function bestEvidence(
  locations: ScannerCVLocation[],
  limit = 3,
): ScannerEvidenceViewModel[] {
  const seen = new Set<string>();
  return [...locations]
    .filter((location) => location.excerpt.trim())
    .sort((left, right) => locationScore(right) - locationScore(left))
    .filter((location) => {
      const key = `${location.section_id ?? ""}|${location.field_path}|${location.excerpt.trim().toLocaleLowerCase()}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, limit)
    .map((location) => ({
      excerpt: location.excerpt.trim(),
      sectionLabel: sectionLabel(location),
      location,
      strength: null,
    }));
}

function semanticEvidence(
  records: Array<ScanResult["semantic"]["evidence"][number]>,
  limit = 3,
): ScannerEvidenceViewModel[] {
  const candidates = records.flatMap((record) => record.locations.map((location) => ({
    excerpt: location.excerpt.trim(),
    sectionLabel: sectionLabel(location),
    location,
    strength: record.strength ?? null,
  })));
  const seen = new Set<string>();
  return candidates
    .filter((item) => item.excerpt)
    .sort((left, right) => {
      const strengthDifference = (right.strength ? STRENGTH_PRIORITY[right.strength] : 0)
        - (left.strength ? STRENGTH_PRIORITY[left.strength] : 0);
      return strengthDifference || locationScore(right.location) - locationScore(left.location);
    })
    .filter((item) => {
      const key = `${item.location.field_path}|${item.excerpt.toLocaleLowerCase()}|${item.strength ?? ""}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, limit);
}

function dedupeEvidence(items: ScannerEvidenceViewModel[], limit = 3): ScannerEvidenceViewModel[] {
  const seen = new Set<string>();
  return [...items]
    .sort((left, right) => {
      const strengthDifference = (right.strength ? STRENGTH_PRIORITY[right.strength] : 0)
        - (left.strength ? STRENGTH_PRIORITY[left.strength] : 0);
      return strengthDifference || locationScore(right.location) - locationScore(left.location);
    })
    .filter((item) => {
      const key = `${item.location.field_path}|${item.excerpt.toLocaleLowerCase()}|${item.strength ?? ""}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, limit);
}

function nodeTitle(node: ScannerExpressionNode, fallback: string): string {
  return node.concept?.name?.trim() || fallback;
}

function requirementTitle(requirement: ScannerRequirement): string {
  const root = requirement.expression;
  if (root.kind === "leaf" && root.concept?.name) return root.concept.name;
  const source = requirement.source.original_text.trim();
  const prefix = source.split(/\b(?:including|such as|e\.g\.|for example)\b/i)[0]?.trim();
  if (prefix && prefix.length <= 90) return prefix.replace(/[,:;.]$/, "");
  return source.length > 90 ? `${source.slice(0, 87).trimEnd()}…` : source;
}

function bucketFor(requirement: ScannerRequirement): ScannerRequirementViewModel["bucket"] {
  if (requirement.classification === "candidate_expectation") return "qualification";
  if (requirement.importance === "preferred") return "preferred";
  if (requirement.importance === "unknown") return "unknown";
  if (requirement.family === "responsibility") return "responsibility";
  return "qualification";
}

function relationLabel(node: ScannerExpressionNode): string | null {
  if (node.kind === "any") return "At least one alternative is required.";
  if (node.kind === "examples") return "Employer examples; not separate requirements.";
  return null;
}

interface FlattenedComponent {
  node: ScannerExpressionNode;
  evaluation: ScannerExpressionEvaluation;
  illustrative: boolean;
  optional: boolean;
}

function flattenComponents(
  node: ScannerExpressionNode,
  evaluation: ScannerExpressionEvaluation,
  options: { illustrative?: boolean; optional?: boolean } = {},
): FlattenedComponent[] {
  if (node.kind === "leaf") {
    return [{
      node,
      evaluation,
      illustrative: options.illustrative ?? false,
      optional: options.optional ?? evaluation.optional,
    }];
  }
  const children = node.kind === "examples"
    ? [
        ...(node.subject ? [{ node: node.subject, illustrative: false }] : []),
        ...(node.examples ?? []).map((child) => ({ node: child, illustrative: true })),
      ]
    : (node.children ?? []).map((child) => ({ node: child, illustrative: options.illustrative ?? false }));
  return children.flatMap(({ node: child, illustrative }) => {
    const childIndex = children.findIndex((item) => item.node.id === child.id);
    const childEvaluation = evaluation.children[childIndex];
    if (!childEvaluation) return [];
    return flattenComponents(child, childEvaluation, {
      illustrative,
      optional: illustrative || childEvaluation.optional,
    });
  });
}

function exampleNames(node: ScannerExpressionNode): string[] {
  if (node.kind === "examples") return (node.examples ?? []).map((item) => nodeTitle(item, "Example"));
  return (node.children ?? []).flatMap(exampleNames);
}

function rootRelation(node: ScannerExpressionNode): string | null {
  return node.kind === "all" ? null : relationLabel(node);
}

function containsKind(node: ScannerExpressionNode, kind: ScannerExpressionNode["kind"]): boolean {
  if (node.kind === kind) return true;
  if (node.kind === "examples") {
    return Boolean(node.subject && containsKind(node.subject, kind))
      || (node.examples ?? []).some((child) => containsKind(child, kind));
  }
  return (node.children ?? []).some((child) => containsKind(child, kind));
}

function coverageSummary(
  requirement: ScannerRequirement,
  components: ScannerComponentViewModel[],
): string {
  if (requirement.expression.kind === "examples") {
    return "The subject is the requirement; the listed technologies are illustrative examples.";
  }
  if (requirement.expression.kind === "any") {
    return requirement.expression.children?.length === 2 && requirement.expression.children[0]?.kind === "any"
      ? "One education field or equivalent practical experience is enough."
      : "One supported alternative is enough; the alternatives are not a checklist.";
  }
  if (containsKind(requirement.expression, "any")) {
    return "This compound requirement contains alternatives; one supported option satisfies each alternative group.";
  }
  const mandatory = components.filter((component) => !component.illustrative && !component.optional);
  if (mandatory.length > 1) {
    const supported = mandatory.filter((component) => component.status === "supported").length;
    return `${supported} of ${mandatory.length} required components covered.`;
  }
  return requirement.source.original_text;
}

function classificationLabel(requirement: ScannerRequirement): string {
  const value = requirement.classification;
  if (!value) return "Candidate-facing requirement";
  return humanize(value);
}

function requirementExplanation(status: ScannerEvidenceStatus, components: ScannerComponentViewModel[]): string {
  if (status === "supported") return "Your CV provides evidence for this requirement.";
  if (status === "partial") {
    const missing = components.filter((component) => !component.illustrative && component.status !== "supported");
    return missing.length > 0
      ? `Your CV supports some of this requirement, but ${missing.map((component) => component.title).join(", ")} still needs evidence.`
      : "Your CV provides some supporting evidence, but the full expectation is not established.";
  }
  if (status === "conflicting") return "The available CV evidence conflicts with this requirement and needs review.";
  if (status === "unverifiable") return "The scanner could not reasonably evaluate this requirement from the available CV representation.";
  return "This CV does not currently show enough evidence for this requirement.";
}

function buildRequirementViewModel(
  requirement: ScannerRequirement,
  evaluation: ScannerRequirementEvaluation | undefined,
  evidenceById: Map<string, ScanResult["semantic"]["evidence"][number]>,
): ScannerRequirementViewModel {
  const fallbackEvaluation: ScannerExpressionEvaluation = {
    node_id: requirement.expression.id,
    status: "not_evidenced",
    optional: false,
    mandatory_total: 0,
    mandatory_supported: 0,
    evidence_ids: [],
    children: [],
  };
  const rootEvaluation = evaluation?.expression ?? fallbackEvaluation;
  const flattened = flattenComponents(requirement.expression, rootEvaluation);
  const components = flattened.map((component) => {
    const records = component.evaluation.evidence_ids
      .map((id) => evidenceById.get(id))
      .filter((record): record is ScanResult["semantic"]["evidence"][number] => Boolean(record));
    const allEvidence = semanticEvidence(records, 100);
    return {
      id: component.node.id,
      title: nodeTitle(component.node, "Requirement component"),
      status: component.evaluation.status,
      optional: component.optional,
      illustrative: component.illustrative,
      evidence: allEvidence.slice(0, 3),
      allEvidence,
    };
  });
  const evidence = dedupeEvidence(components.flatMap((component) => component.allEvidence));
  const status = evaluation?.status ?? "not_evidenced";
  const importance = requirement.importance;
  const expectation = requirement.classification === "candidate_expectation";
  return {
    id: requirement.id,
    title: requirementTitle(requirement),
    sourceText: requirement.source.original_text,
    importance,
    importanceLabel: expectation ? "Expectation" : importance === "required" ? "Required" : importance === "preferred" ? "Preferred" : "Unclassified",
    status,
    statusLabel: statusLabel(status),
    bucket: bucketFor(requirement),
    components,
    examples: exampleNames(requirement.expression),
    relationLabel: rootRelation(requirement.expression),
    coverageSummary: coverageSummary(requirement, components),
    classificationLabel: classificationLabel(requirement),
    evidence,
    explanation: requirementExplanation(status, components),
    unclassified: importance === "unknown" && !expectation,
  };
}

function keywordCategory(term: ScannerLexicalTerm): ScannerKeywordCategory {
  if (term.illustrative_example) return "employer_vocabulary";
  if (term.visibility !== "absent") return "visible";
  if (term.semantic_support === "supported") return "safe_wording";
  if (term.semantic_support === "partial") return "review_before_adding";
  return "unsupported";
}

function keywordCategoryLabel(category: ScannerKeywordCategory): string {
  return {
    safe_wording: "Safe wording opportunity",
    review_before_adding: "Review before adding",
    unsupported: "Not shown or unsupported",
    employer_vocabulary: "Employer vocabulary",
    visible: "Visible in your CV",
  }[category];
}

function buildKeywordViewModel(term: ScannerLexicalTerm): ScannerKeywordViewModel {
  const category = keywordCategory(term);
  const allEvidence = bestEvidence(term.evidence.map((item) => item.location), 100);
  return {
    id: term.id,
    term: term.term,
    category,
    categoryLabel: keywordCategoryLabel(category),
    visibility: term.visibility,
    visibilityLabel: VISIBILITY_LABELS[term.visibility],
    semanticSupport: term.semantic_support ?? null,
    occurrenceCount: term.evidence.length,
    evidence: allEvidence.slice(0, 3),
    allEvidence,
    illustrative: term.illustrative_example,
    employerVocabulary: category === "employer_vocabulary",
  };
}

function checkValue(check: ScanResult["pdf_recovery"]["checks"][number]): number | null {
  if (check.expected_count === null || check.recovered_count === null || check.expected_count <= 0) return null;
  return Math.min(1, check.recovered_count / check.expected_count);
}

function buildCheckViewModel(check: ScanResult["pdf_recovery"]["checks"][number]): ScannerAtsCheckViewModel {
  return {
    code: check.code,
    label: CHECK_LABELS[check.code] ?? humanize(check.code),
    status: check.status,
    statusLabel: check.status === "pass" ? "Pass" : check.status === "warning" ? "Warning" : check.status === "fail" ? "Needs attention" : "Unavailable",
    value: checkValue(check),
    recoveredCount: check.recovered_count,
    expectedCount: check.expected_count,
    expectedItems: check.expected_items ?? [],
    recoveredItems: check.recovered_items ?? [],
    missingItems: check.missing_items ?? [],
    affectedItems: check.affected_items ?? [],
    explanation: check.explanation ?? "No additional details are available.",
  };
}

function buildAtsFindingViewModel(finding: ScannerAtsFinding): ScannerAtsFindingViewModel {
  return {
    ...finding,
    severityLabel: finding.severity === "pass"
      ? "Pass"
      : finding.severity === "warning"
        ? "Needs attention"
        : finding.severity === "recommendation"
          ? "Recommendation"
          : "Information",
    categoryLabel: ATS_CATEGORY_LABELS[finding.category] ?? humanize(finding.category),
  };
}

function buildAtsGuidanceViewModel(guidance: ScanResult["ats_guidance"]): ScannerAtsGuidanceViewModel {
  if (!guidance) {
    return {
      available: false,
      commonFindings: [],
      platformSensitiveFindings: [],
      platforms: {},
      headingConventions: [],
      dateCompatibility: [],
      acronymCoverage: [],
      entryCompleteness: [],
      summary: null,
    };
  }
  return {
    available: true,
    commonFindings: guidance.common_findings.map(buildAtsFindingViewModel),
    platformSensitiveFindings: guidance.platform_sensitive_findings.map(buildAtsFindingViewModel),
      platforms: Object.fromEntries(
        Object.entries(guidance.platforms).map(([id, platform]) => [id, {
          ...platform,
          findings: platform.findings.map(buildAtsFindingViewModel),
          tips: platform.tips.map(buildAtsFindingViewModel),
        }]),
      ),
    headingConventions: guidance.heading_conventions,
    dateCompatibility: guidance.date_compatibility,
    acronymCoverage: guidance.acronym_coverage,
    entryCompleteness: guidance.entry_completeness,
    summary: guidance.summary,
  };
}

function qualityStatus(result: ScanResult): ScannerReportViewModel["quality"]["status"] {
  if (result.presentation_quality.status !== "evaluated") return "unavailable";
  if (result.presentation_quality.findings.some((finding) => finding.severity === "error")) return "at_risk";
  if (result.presentation_quality.findings.some((finding) => finding.severity === "warning")) return "needs_attention";
  return "looks_good";
}

function pdfStatus(result: ScanResult): ScannerReportViewModel["pdf"]["status"] {
  return result.pdf_recovery.status;
}

function atsStatus(result: ScanResult): ScannerReportViewModel["ats"]["status"] {
  const statuses = result.pdf_recovery.checks.map((check) => check.status);
  const hasGuidance = Boolean(result.ats_guidance);
  if ((statuses.length === 0 || statuses.every((status) => status === "unavailable")) && !hasGuidance) return "unavailable";
  if (statuses.some((status) => status === "fail")) return "at_risk";
  if (statuses.some((status) => status === "warning" || status === "unavailable")) return "needs_attention";
  if (result.ats_guidance?.common_findings.some((finding) => finding.severity === "warning" || finding.severity === "recommendation")) return "needs_attention";
  return "looks_good";
}

function statusForBadge(application: Application): ScannerBadgeViewModel {
  const result = application.scanner_result ?? null;
  const state = (application.scanner_status ?? (result ? "current" : "not_scanned")) as ScannerBadgeState;
  const score = result?.semantic.summary?.job_fit ?? null;
  if (state === "not_scanned") return { state, label: "Analyze CV", score: null, stale: false, disabled: !application.cv_id };
  if (state === "needs_rescan") return { state, label: score === null ? "Job Fit · Update needed" : `Job Fit ${percentage(score)} · Update needed`, score, stale: true, disabled: !application.cv_id };
  if (state === "stale") return { state, label: score === null ? "Job Fit · Update needed" : `Job Fit ${percentage(score)} · Update needed`, score, stale: true, disabled: !application.cv_id };
  if (state === "unavailable") return { state, label: "Job Fit —", score: null, stale: false, disabled: !application.cv_id };
  return { state: "current", label: score === null ? "Job Fit —" : `Job Fit ${percentage(score)}`, score, stale: false, disabled: false };
}

export function scannerBadgeState(application: Application): ScannerBadgeViewModel {
  return statusForBadge(application);
}

export function scannerStatusLabel(state: ScannerBadgeState): string {
  return {
    current: "Current",
    stale: "Needs rescan",
    needs_rescan: "Needs rescan",
    not_scanned: "Not scanned",
    unavailable: "Unavailable",
  }[state];
}

export function formatScannerPercent(value: number | null | undefined): string {
  return percentage(value);
}

export function buildScannerReportViewModel(result: ScanResult, application: Application): ScannerReportViewModel {
  const summary = result.semantic.summary;
  const evidenceById = new Map(result.semantic.evidence.map((item) => [item.id, item]));
  const evaluationById = new Map(result.semantic.requirements.map((item) => [item.requirement_id, item]));
  const requirements = result.requirement_extraction.requirements.map((requirement) =>
    buildRequirementViewModel(requirement, evaluationById.get(requirement.id), evidenceById),
  );
  const sortedNeeds = [...requirements].sort((left, right) => {
    const importanceRank = { required: 0, preferred: 1, unknown: 2 } as const;
    return (importanceRank[left.importance] - importanceRank[right.importance])
      || (STATUS_PRIORITY[left.status] - STATUS_PRIORITY[right.status])
      || left.title.localeCompare(right.title);
  });
  const keywords = result.lexical.terms.map(buildKeywordViewModel);
  const qualityFindings = result.presentation_quality.findings.map((finding) => ({
    code: finding.code,
    label: humanize(finding.code),
    severity: finding.severity,
    severityLabel: finding.severity === "error" ? "Error" : finding.severity === "warning" ? "Warning" : "Suggestion",
    evidence: finding.evidence,
    explanation: finding.explanation,
    locationLabel: finding.location ? sectionLabel(finding.location) : "Document",
  }));
  const pdfChecks = result.pdf_recovery.checks.map(buildCheckViewModel);
  const covered = requirements.filter((requirement) => requirement.status === "supported");
  const gaps = sortedNeeds.filter((requirement) => requirement.status !== "supported");
  const score = summary?.job_fit ?? null;
  const ats = atsStatus(result);
  const atsGuidance = buildAtsGuidanceViewModel(result.ats_guidance);
  const quality = qualityStatus(result);
  return {
    badge: statusForBadge(application),
    score: {
      status: summary?.status ?? "unavailable",
      jobFit: score,
      classifiedFraction: summary?.classified_fraction ?? null,
      evidenceScorableFraction: summary?.evidence_scorable_fraction ?? summary?.scorable_fraction ?? null,
      lowClassificationWarning: summary?.classification_warning_code === "low_requirement_classification_coverage",
      coveredCount: summary?.supported_requirement_count ?? summary?.supported_count ?? covered.length,
      partialCount: summary?.partial_requirement_count ?? summary?.partial_count ?? 0,
      notShownCount: summary?.not_evidenced_requirement_count ?? summary?.not_evidenced_count ?? 0,
      conflictingCount: summary?.conflicting_requirement_count ?? summary?.conflicting_count ?? 0,
      unverifiableCount: summary?.unverifiable_requirement_count ?? summary?.unverifiable_count ?? 0,
      unverifiableComponentCount: summary?.unverifiable_component_count ?? 0,
      requiredConstraintConflicts: summary?.required_constraint_conflicts ?? 0,
      buckets: {
        qualifications: { label: "Core qualifications", score: summary?.qualification_fit.score ?? null, scorableFraction: summary?.qualification_fit.scorable_fraction ?? 0, totalWeight: summary?.qualification_fit.total_weight ?? 0, requirementCount: summary?.qualification_fit.requirement_count ?? 0 },
        responsibilities: { label: "Responsibilities", score: summary?.responsibility_alignment.score ?? null, scorableFraction: summary?.responsibility_alignment.scorable_fraction ?? 0, totalWeight: summary?.responsibility_alignment.total_weight ?? 0, requirementCount: summary?.responsibility_alignment.requirement_count ?? 0 },
        preferred: { label: "Preferred qualifications", score: summary?.preferred_fit.score ?? null, scorableFraction: summary?.preferred_fit.scorable_fraction ?? 0, totalWeight: summary?.preferred_fit.total_weight ?? 0, requirementCount: summary?.preferred_fit.requirement_count ?? 0 },
      },
    },
    requirements,
    strengths: covered.slice(0, 6),
    gaps,
    keywords: {
      visibilityScore: result.lexical.summary?.visibility_score ?? null,
      exactCount: result.lexical.summary?.exact_count ?? 0,
      normalizedCount: result.lexical.summary?.normalized_count ?? 0,
      variantCount: result.lexical.summary?.variant_count ?? 0,
      absentCount: result.lexical.summary?.absent_count ?? 0,
      safeWording: keywords.filter((term) => term.category === "safe_wording"),
      reviewBeforeAdding: keywords.filter((term) => term.category === "review_before_adding"),
      unsupported: keywords.filter((term) => term.category === "unsupported"),
      employerVocabulary: keywords.filter((term) => term.category === "employer_vocabulary"),
      visible: keywords.filter((term) => term.category === "visible"),
    },
    ats: {
      status: ats,
      statusLabel: ats === "looks_good" ? "Looks good" : ats === "at_risk" ? "At risk" : ats === "unavailable" ? "Unavailable" : "Needs attention",
      checks: pdfChecks,
      guidance: atsGuidance,
    },
    quality: {
      status: quality,
      statusLabel: quality === "looks_good" ? "Looks good" : quality === "at_risk" ? "At risk" : quality === "unavailable" ? "Unavailable" : "Needs attention",
      errorCount: qualityFindings.filter((finding) => finding.severity === "error").length,
      warningCount: qualityFindings.filter((finding) => finding.severity === "warning").length,
      infoCount: qualityFindings.filter((finding) => finding.severity === "info").length,
      findings: qualityFindings,
      bulletAssessmentCount: result.presentation_quality.bullet_assessments.length,
    },
    pdf: {
      status: pdfStatus(result),
      statusLabel: result.pdf_recovery.status === "pass" ? "Pass" : result.pdf_recovery.status === "warning" ? "Needs attention" : result.pdf_recovery.status === "fail" ? "At risk" : "Unavailable",
      recoveryScore: result.pdf_recovery.summary?.recovery_score ?? null,
      checks: pdfChecks,
      disclaimer: "These checks describe what Aergia recovered from this PDF. They do not guarantee behavior in every ATS.",
    },
    diagnostics: {
      versions: result.versions,
      extractionWarnings: result.requirement_extraction.warnings,
      fingerprints: result.input_fingerprints,
      raw: result,
    },
  };
}

export function statusText(status: ScannerEvidenceStatus): string {
  return statusLabel(status);
}

export function evidenceStrengthText(strength: ScannerEvidenceStrength | null | undefined): string | null {
  return strength ? STRENGTH_LABELS[strength] : null;
}

export function componentStatusIcon(status: ScannerEvidenceStatus): "check" | "partial" | "missing" | "conflict" | "unknown" {
  if (status === "supported") return "check";
  if (status === "partial") return "partial";
  if (status === "conflicting") return "conflict";
  if (status === "not_evidenced") return "missing";
  return "unknown";
}
