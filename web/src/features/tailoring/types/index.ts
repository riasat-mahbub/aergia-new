import type { ScanResult } from "@/features/applications";

export type TailoringReadinessStatus = "ready" | "ready_with_review" | "revise" | "blocked";

export interface TailoringInferenceNote {
  claim: string;
  basis: string[];
  confidence: "entailed" | "strong" | "reasonable" | "speculative";
  section_id?: string | null;
  item_id?: string | null;
  field_path?: string | null;
  review_recommended: boolean;
}

export interface TailoringIssue {
  id: string;
  kind: "blocker" | "review" | "recommendation" | "non_actionable_gap";
  category: string;
  message: string;
  detail?: string | null;
  priority: "high" | "normal" | "low";
  requirement_id?: string | null;
  term_id?: string | null;
  code?: string | null;
  importance?: string | null;
}

export interface TailoringEvaluation {
  version: "tailoring-evaluation-v1";
  candidate_hash: string;
  pass_number: number;
  source_comparison: {
    available: boolean;
    requirement_transitions: Array<{
      requirement_id: string;
      importance: string;
      source_status?: string | null;
      candidate_status?: string | null;
      classification: "improved" | "regressed" | "unchanged" | "changed_needs_review";
      label: string;
    }>;
    keyword_transitions: Array<{
      term_id: string;
      term: string;
      source_visibility?: string | null;
      candidate_visibility?: string | null;
      semantic_support?: string | null;
      classification: "improved" | "regressed" | "unchanged" | "changed_needs_review";
    }>;
  };
  previous_pass_comparison: {
    available: boolean;
    previous_candidate_hash?: string | null;
    candidate_hash: string;
    changes: Array<{
      id: string;
      area: string;
      classification: "fixed" | "introduced" | "improved" | "regressed";
      message: string;
      requirement_id?: string | null;
      term_id?: string | null;
    }>;
    job_fit_delta?: number | null;
    term_visibility_delta?: number | null;
  };
  dimensions: {
    job_fit: { source?: number | null; candidate?: number | null };
    keywords: { source?: number | null; candidate?: number | null };
    ats: {
      source_count?: number | null;
      candidate_count: number;
      candidate_error_count: number;
      candidate_warning_count: number;
      candidate_info_count: number;
    };
    resume_quality: {
      source_count?: number | null;
      candidate_count: number;
      candidate_error_count: number;
      candidate_warning_count: number;
      candidate_info_count: number;
    };
    pdf_recovery: { source?: number | null; candidate?: number | null };
  };
  improvements: TailoringIssue[];
  regressions: TailoringIssue[];
  blockers: TailoringIssue[];
  review_items: TailoringIssue[];
  recommendations: TailoringIssue[];
  non_actionable_gaps: TailoringIssue[];
  inference_notes: TailoringInferenceNote[];
  render_warnings: string[];
  readiness: {
    status: TailoringReadinessStatus;
    submission_allowed: boolean;
    reasons: string[];
  };
}

export interface TailoringEditorialFinding {
  category: "evidence_selection" | "framing" | "impact" | "clarity" | "natural_writing" | "visual_balance";
  severity: "important" | "polish" | "blocking";
  section_id: string;
  item_id?: string | null;
  field_path?: string | null;
  excerpt: string;
  problem: string;
  recommended_change: string;
}

export interface TailoringEditorialReview {
  review_version: "aergia-editorial-review-v1";
  candidate_hash: string;
  pass_number: number;
  findings: TailoringEditorialFinding[];
  inference_notes: TailoringInferenceNote[];
}

export interface TailoringSession {
  protocol_version: 5;
  session_id: string;
  application_id: string;
  source_cv_id: string | null;
  cv_id: string | null;
  code: string;
  session_url: string;
  skill_url: string;
  prompt: string;
  status: "created";
  expires_at: string;
}

export type TailoringSessionStatus =
  | "created"
  | "exchanged"
  | "draft_ready"
  | "accepted"
  | "rejected"
  | "failed"
  | "expired"
  | "cancelled"
  | "stale";

export interface TailoringCandidate {
  id?: string | null;
  title: string;
  description?: string | null;
  template_id: string;
  sections: Array<Record<string, unknown>>;
  customizations: Record<string, unknown>;
}

export interface TailoringSessionResult {
  protocol_version: 4 | 5;
  session_id: string;
  application_id: string;
  status: "draft_ready";
  source_cv_id: string | null;
  draft_cv_id: string;
  candidate_hash: string;
  candidate?: TailoringCandidate;
  scanner_result?: ScanResult | null;
  evaluation?: TailoringEvaluation | null;
  tailoring_evaluation?: TailoringEvaluation | null;
  inference_notes?: TailoringInferenceNote[];
  editorial_review?: TailoringEditorialReview | null;
  render_warnings?: string[];
  review_notes?: string[];
}

export interface TailoringSessionStatusResponse {
  protocol_version: 4 | 5;
  session_id: string;
  application_id: string;
  source_cv_id: string | null;
  draft_cv_id: string | null;
  cv_id: string | null;
  status: TailoringSessionStatus;
  expires_at: string;
  created_at: string;
  exchanged_at: string | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  updated_at: string;
  attempts: number;
  result: TailoringSessionResult | null;
}

export interface TailoringReviewResponse {
  protocol_version: 4 | 5;
  session_id: string;
  application_id: string;
  status: "accepted" | "rejected";
  source_cv_id: string | null;
  draft_cv_id: string | null;
  cv_id: string | null;
  scanner_result: ScanResult | null;
}
