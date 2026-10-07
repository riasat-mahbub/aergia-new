import client from "@/shared/api/client";
import type {
  TailoringAcceptRequest,
  TailoringDraftContextResponse,
  TailoringReevaluateRequest,
  TailoringReevaluateResponse,
  TailoringReviewResponse,
  TailoringSessionCreateResponse,
  TailoringSessionStatusResponse,
} from "../types";

export async function createTailoringSession(applicationId: string): Promise<TailoringSessionCreateResponse> {
  const { data } = await client.post(`/applications/${applicationId}/tailoring-sessions?protocol_version=10`);
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

export async function acceptTailoringDraft(
  sessionId: string,
  request?: TailoringAcceptRequest,
): Promise<TailoringReviewResponse> {
  // Omitting the body is retained for owner review of protocols 4–9.
  const { data } = await client.post(`/tailoring/sessions/${sessionId}/accept`, request);
  return data;
}

export async function reevaluateTailoringDraft(
  sessionId: string,
  request: TailoringReevaluateRequest,
): Promise<TailoringReevaluateResponse> {
  const { data } = await client.post(`/tailoring/sessions/${sessionId}/reevaluate`, request);
  return data;
}

export async function getTailoringDraftContext(cvId: string): Promise<TailoringDraftContextResponse> {
  const { data } = await client.get(`/cvs/${cvId}/tailoring-context`);
  return data;
}

export async function rejectTailoringDraft(sessionId: string): Promise<TailoringReviewResponse> {
  const { data } = await client.post(`/tailoring/sessions/${sessionId}/reject`);
  return data;
}
