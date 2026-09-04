import client from "./client";
import type { CVCreateData, CVDetail, CVListItem, CVUpdateData } from "@/contracts/cvs";

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
