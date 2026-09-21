import type { ScanResult } from "@/features/applications";

export interface TailoringSession {
  protocol_version: 4;
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
  protocol_version: 4;
  session_id: string;
  application_id: string;
  status: "draft_ready";
  source_cv_id: string | null;
  draft_cv_id: string;
  candidate_hash: string;
  candidate?: TailoringCandidate;
  scanner_result: ScanResult;
  render_warnings: string[];
  review_notes?: string[];
}

export interface TailoringSessionStatusResponse {
  protocol_version: 4;
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
  protocol_version: 4;
  session_id: string;
  application_id: string;
  status: "accepted" | "rejected";
  source_cv_id: string | null;
  draft_cv_id: string | null;
  cv_id: string | null;
  scanner_result: ScanResult | null;
}
