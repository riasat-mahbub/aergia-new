import client from "@/shared/api/client";
import type {
  TailoringReviewResponse,
  TailoringSessionCreateResponse,
  TailoringSessionStatusResponse,
} from "../types";

export async function createTailoringSession(applicationId: string): Promise<TailoringSessionCreateResponse> {
  const { data } = await client.post(`/applications/${applicationId}/tailoring-sessions?protocol_version=9`);
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
