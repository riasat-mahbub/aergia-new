import client from "./client";

export interface CVApplicationSummary {
  id: string;
  company: string;
  role: string;
  status: "draft" | "applied" | "responded" | "interview" | "offer" | "hired" | "rejected" | "withdrawn";
  generation_status: "pending" | "ready" | "failed";
  applied_at: string | null;
}

export interface CVListItem {
  id: string;
  title: string;
  template_id: string;
  created_at: string;
  updated_at: string;
  application?: CVApplicationSummary | null;
}

export interface CVDetail {
  id: string;
  title: string;
  description: string | null;
  template_id: string;
  customizations: Record<string, unknown>;
  sections: unknown;
  extra_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CVCreateData {
  title: string;
  description?: string;
  template_id?: string;
  sections?: unknown;
  customizations?: Record<string, unknown>;
}

export interface CVUpdateData {
  title?: string;
  description?: string;
  template_id?: string;
  sections?: unknown;
  customizations?: Record<string, unknown>;
}

export async function fetchCVs(): Promise<CVListItem[]> {
  const { data } = await client.get("/cvs");
  return data;
}

export async function fetchCV(id: string): Promise<CVDetail> {
  const { data } = await client.get(`/cvs/${id}`);
  return data;
}

export async function createCV(input: CVCreateData): Promise<CVDetail> {
  const { data } = await client.post("/cvs", input);
  return data;
}

export async function updateCV(id: string, input: CVUpdateData): Promise<CVDetail> {
  const { data } = await client.patch(`/cvs/${id}`, input);
  return data;
}

export async function deleteCV(id: string): Promise<void> {
  await client.delete(`/cvs/${id}`);
}

export async function copyCV(id: string): Promise<CVDetail> {
  const { data } = await client.post(`/cvs/${id}/copy`);
  return data;
}

export async function exportPDF(id: string): Promise<Blob> {
  const { data } = await client.post(`/cvs/${id}/export/pdf`, null, {
    responseType: "blob",
  });
  return data;
}


export function downloadPDF(blob: Blob, filename: string = "cv.pdf") {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
