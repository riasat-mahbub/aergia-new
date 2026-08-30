import client from "./client";

export interface TailoringSession {
  protocol_version: 1;
  session_id: string;
  application_id: string;
  cv_id: string;
  code: string;
  expires_at: string;
}

export async function createTailoringSession(applicationId: string): Promise<TailoringSession> {
  const { data } = await client.post(`/applications/${applicationId}/tailoring-sessions`);
  return data;
}
