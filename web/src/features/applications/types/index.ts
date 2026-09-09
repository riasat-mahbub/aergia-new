export const APPLICATION_STATUSES = [
  "draft",
  "applied",
  "responded",
  "interview",
  "offer",
  "hired",
  "rejected",
  "withdrawn",
] as const;

export type ApplicationStatus = (typeof APPLICATION_STATUSES)[number];
export type GenerationStatus = "pending" | "ready" | "failed";
export type CVQualityStatus = "pass" | "warning" | "error";
export type CVQualityIssueCode = "missing_name" | "missing_contact" | "empty_section" | "invalid_link" | "page_overflow";

export interface ExtractedKeyword {
  text: string;
  normalized: string;
  weight: number;
}

export interface MatchEvidence {
  keyword: string;
  section_type: string;
  library_entry_id: string | null;
  source_row_id: string | null;
  field_path: string;
  snippet: string;
}

export interface RelevanceResult {
  score: number;
  matched_weight: number;
  total_weight: number;
  matched_keywords: string[];
  missing_keywords: string[];
  evidence: MatchEvidence[];
  algorithm_version: string;
}

export type RequirementType = "hard_skill" | "responsibility" | "quantitative" | "education" | "certification" | "language" | "project" | "research" | "other";
export type RequirementImportance = "required" | "preferred" | "unknown";

export interface JobRequirement {
  id: string;
  text: string;
  normalized: string;
  canonical?: string | null;
  type: RequirementType;
  required: boolean;
  weight: number;
  constraint?: Record<string, unknown> | null;
  importance?: RequirementImportance | null;
  concepts?: string[];
  constraints?: Array<Record<string, unknown>>;
  source_start?: number | null;
  source_end?: number | null;
  confidence?: number;
  extractor?: string;
  extractor_version?: string;
}

export interface RequirementEvidence {
  section_type: string;
  library_entry_id: string | null;
  source_row_id: string | null;
  field_path: string;
  snippet: string;
  method: "taxonomy" | "constraint" | "fts5" | "fuzzy";
  score: number;
}

export interface RequirementMatch {
  requirement: JobRequirement;
  covered: boolean;
  score: number;
  matched_by: string[];
  best_evidence: RequirementEvidence | null;
  tailoring_feedback?: string[];
}

export interface RequirementRelevanceResult {
  status: "not_evaluated" | "evaluated";
  score: number | null;
  coverage_score?: number | null;
  required_score?: number | null;
  preferred_score?: number | null;
  matched_weight: number;
  total_weight: number;
  covered_requirements: number;
  total_requirements: number;
  requirements: RequirementMatch[];
  algorithm_version: string;
  ai_relevance?: AIRelevanceResult | null;
}

export interface AIRelevanceEvidence {
  section_id: string;
  entry_id?: string | null;
  field_path: string;
  excerpt: string;
}

export interface AIRequirementMatch {
  requirement_id: string;
  coverage: "absent" | "weak" | "partial" | "strong" | "excellent";
  score: number;
  confidence: number;
  evidence: AIRelevanceEvidence[];
  rationale: string;
}

export interface AIRelevanceResult {
  status: "evaluated";
  score: number;
  required_score?: number | null;
  preferred_score?: number | null;
  confidence?: number | null;
  requirements: AIRequirementMatch[];
  rubric_version: string;
  evaluation_mode: "independent_pass" | "same_agent_pass";
  evaluator?: string | null;
}

export type RelevanceAnalysis = RelevanceResult | RequirementRelevanceResult;

export interface ApplicationStatusHistory {
  id: string;
  from_status: ApplicationStatus | null;
  to_status: ApplicationStatus;
  changed_at: string;
}

export interface CVQualityIssue {
  code: CVQualityIssueCode;
  severity: "warning" | "error";
  message: string;
  section_type?: string | null;
  field_path?: string | null;
}

export interface CVQualityResult {
  status: CVQualityStatus;
  page_count: number | null;
  issues: CVQualityIssue[];
}

export interface Application {
  id: string;
  user_id?: string;
  cv_id: string | null;
  company: string;
  role: string;
  job_url: string | null;
  job_description: string;
  notes: string | null;
  status: ApplicationStatus;
  applied_at: string | null;
  next_follow_up_at?: string | null;
  status_history?: ApplicationStatusHistory[];
  generation_status: GenerationStatus;
  generation_error: string | null;
  extracted_keywords: ExtractedKeyword[];
  relevance: RelevanceAnalysis | Record<string, never>;
  algorithm_version: string;
  fits_one_page: boolean | null;
  quality?: CVQualityResult | Record<string, never>;
  created_at: string;
  updated_at: string;
}

export interface ApplicationCreateData {
  company: string;
  role: string;
  job_description: string;
  job_url?: string;
  notes?: string;
  next_follow_up_at?: string | null;
}

export interface ApplicationUpdateData {
  company?: string;
  role?: string;
  job_description?: string;
  job_url?: string | null;
  notes?: string | null;
  next_follow_up_at?: string | null;
  status?: ApplicationStatus;
  applied_at?: string | null;
}

export interface ApplicationGenerateResponse {
  application: Application;
  cv_id: string | null;
}
