import client from "@/services/client";
import type {
  TailoringSession,
  TailoringSessionStatusResponse,
} from "../_types/tailoring";

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
