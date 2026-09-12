import client from "@/shared/api/client";
import type {
  TailoringReviewResponse,
  TailoringSession,
  TailoringSessionStatusResponse,
} from "../types";

export async function createTailoringSession(applicationId: string): Promise<TailoringSession> {
  const { data } = await client.post(`/applications/${applicationId}/tailoring-sessions`);
  return data;
}

export async function getTailoringSessionStatus(sessionId: string): Promise<TailoringSessionStatusResponse> {
  const { data } = await client.get(`/tailoring/sessions/${sessionId}`);
  return data;
}

export async function getLatestTailoringSession(applicationId: string): Promise<TailoringSessionStatusResponse> {
  const { data } = await client.get(`/applications/${applicationId}/tailoring-sessions/latest`);
  return data;
}

export async function cancelTailoringSession(sessionId: string): Promise<TailoringSessionStatusResponse> {
  const { data } = await client.post(`/tailoring/sessions/${sessionId}/cancel`);
  return data;
}

export async function acceptTailoringDraft(sessionId: string): Promise<TailoringReviewResponse> {
  const { data } = await client.post(`/tailoring/sessions/${sessionId}/accept`);
  return data;
}

export async function rejectTailoringDraft(sessionId: string): Promise<TailoringReviewResponse> {
  const { data } = await client.post(`/tailoring/sessions/${sessionId}/reject`);
  return data;
}
