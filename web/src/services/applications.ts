import client from "./client";
import type {
  Application,
  ApplicationCreateData,
  ApplicationGenerateResponse,
  ApplicationUpdateData,
} from "@/contracts/applications";

export async function listApplications(): Promise<Application[]> {
  const { data } = await client.get("/applications");
  return data;
}

export async function getApplication(id: string): Promise<Application> {
  const { data } = await client.get(`/applications/${id}`);
  return data;
}

export async function createApplication(input: ApplicationCreateData): Promise<Application> {
  const { data } = await client.post("/applications", input);
  return data;
}

export async function updateApplication(id: string, input: ApplicationUpdateData): Promise<Application> {
  const { data } = await client.patch(`/applications/${id}`, input);
  return data;
}

export async function deleteApplication(id: string): Promise<void> {
  await client.delete(`/applications/${id}`);
}

export async function generateApplication(id: string): Promise<ApplicationGenerateResponse> {
  const { data } = await client.post(`/applications/${id}/generate`);
  return data;
}

export async function recomputeApplicationRelevance(id: string): Promise<Application> {
  const { data } = await client.post(`/applications/${id}/relevance`);
  return data;
}
