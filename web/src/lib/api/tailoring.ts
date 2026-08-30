import client from "./client";

export interface TailoringSession {
  protocol_version: 1;
  session_id: string;
  application_id: string;
  cv_id: string;
  code: string;
  session_url: string;
  prompt: string;
  status: "created";
  expires_at: string;
}

export type TailoringSessionStatus =
  | "created"
  | "exchanged"
  | "submitted"
  | "applied"
  | "failed"
  | "expired"
  | "cancelled"
  | "stale";

export interface TailoringSessionResult {
  protocol_version: 1;
  session_id: string;
  application_id: string;
  cv_id: string;
  base_revision: number;
  new_revision: number;
  applied_operations: string[];
  gaps: Array<{ requirement: string; reason: string }>;
  provenance: Array<Record<string, unknown>>;
  before_relevance: Record<string, unknown>;
  relevance: Record<string, unknown>;
}

export interface TailoringSessionStatusResponse {
  protocol_version: 1;
  session_id: string;
  application_id: string;
  cv_id: string;
  status: TailoringSessionStatus;
  expires_at: string;
  created_at: string;
  exchanged_at: string | null;
  submitted_at: string | null;
  updated_at: string;
  attempts: number;
  reported_gaps: Array<{ requirement: string; reason: string }>;
  result: TailoringSessionResult | null;
}

export async function createTailoringSession(applicationId: string): Promise<TailoringSession> {
  const { data } = await client.post(`/applications/${applicationId}/tailoring-sessions`);
  return data;
}

export async function getTailoringSessionStatus(sessionId: string): Promise<TailoringSessionStatusResponse> {
  const { data } = await client.get(`/tailoring/sessions/${sessionId}`);
  return data;
}

export async function cancelTailoringSession(sessionId: string): Promise<TailoringSessionStatusResponse> {
  const { data } = await client.post(`/tailoring/sessions/${sessionId}/cancel`);
  return data;
}
