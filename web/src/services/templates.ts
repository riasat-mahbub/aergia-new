import client from "./client";
import type { UserTemplate } from "@/contracts/templates";

export async function fetchSystemTemplates(): Promise<UserTemplate[]> {
  const { data } = await client.get("/templates");
  return data;
}

export async function fetchTemplate(templateId: string): Promise<UserTemplate> {
  const { data } = await client.get(`/templates/${templateId}`);
  return data;
}
