import type { ScanResult } from "@/features/applications";

export type HistoricalTailoringProtocolVersion = 4 | 5 | 6 | 7 | 8;
export type TailoringProtocolVersion = HistoricalTailoringProtocolVersion | 9;

export interface TailoringIssue {
  id: string;
  kind: "risk" | "blocker" | "review" | "recommendation" | "non_actionable_gap";
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
  version: "tailoring-evaluation-v1" | "tailoring-evaluation-v2";
  candidate_hash: string;
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
  previous_evaluation_comparison?: {
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
  risk_findings?: TailoringIssue[];
  /** Historical v1 advisory bucket. Render these as concerns in the review UI. */
  blockers?: TailoringIssue[];
  review_items: TailoringIssue[];
  recommendations: TailoringIssue[];
  non_actionable_gaps: TailoringIssue[];
  render_warnings: string[];
}

/** Stored only on historical protocol-v8 results. Protocol v9 has no editorial review payload. */
export interface TailoringEditorialFinding {
  category: "evidence_selection" | "targeting" | "framing" | "impact" | "clarity" | "natural_writing" | "visual_balance";
  severity: "important" | "polish" | "blocking";
  section_id: string;
  item_id?: string | null;
  field_path?: string | null;
  excerpt: string;
  problem: string;
  recommended_change: string;
}

export interface TailoringEditorialReview {
  review_version: "aergia-editorial-review-v2";
  evaluation_id: string;
  candidate_hash: string;
  findings: TailoringEditorialFinding[];
}

export interface HistoricalTailoringEditorialReview {
  review_version: "aergia-editorial-review-v1";
  candidate_hash: string;
  findings: TailoringEditorialFinding[];
}

export interface TailoringSession {
  protocol_version: TailoringProtocolVersion;
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

/** Newly created sessions use the active whole-dossier protocol. */
export type TailoringSessionCreateResponse = Omit<TailoringSession, "protocol_version"> & {
  protocol_version: 9;
};

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

interface TailoringSessionResultBase {
  session_id: string;
  application_id: string;
  status: "draft_ready";
  source_cv_id: string | null;
  draft_cv_id: string;
  scanner_result?: ScanResult | null;
  evaluation?: TailoringEvaluation | null;
  tailoring_evaluation?: TailoringEvaluation | null;
  render_warnings?: string[];
  review_notes?: string[];
}

/** The compact historical result variants remain readable for owner review. */
export type TailoringSessionResult =
  | (TailoringSessionResultBase & {
      protocol_version: Exclude<HistoricalTailoringProtocolVersion, 8>;
      evaluation_id?: string;
      candidate_hash?: string;
      candidate?: TailoringCandidate;
      editorial_review?: never;
    })
  | (TailoringSessionResultBase & {
      protocol_version: 8;
      evaluation_id?: string;
      candidate_hash: string;
      candidate?: TailoringCandidate;
      editorial_review?: TailoringEditorialReview | HistoricalTailoringEditorialReview | null;
    })
  | (TailoringSessionResultBase & {
      protocol_version: 9;
      evaluation_id: string;
      candidate_hash: string;
      candidate: TailoringCandidate;
      editorial_review?: never;
    });

export interface TailoringSessionStatusResponse {
  protocol_version: TailoringProtocolVersion;
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
  protocol_version: TailoringProtocolVersion;
  session_id: string;
  application_id: string;
  status: "accepted" | "rejected";
  source_cv_id: string | null;
  draft_cv_id: string | null;
  cv_id: string | null;
  scanner_result: ScanResult | null;
}
