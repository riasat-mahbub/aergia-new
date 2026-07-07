import client from "./client";

export interface UserTemplate {
  id: string;
  name: string;
  description: string | null;
  preview_image_url: string | null;
  manifest: Record<string, any> | null;
}

export async function fetchSystemTemplates(): Promise<UserTemplate[]> {
  const { data } = await client.get("/templates");
  return data;
}

export async function fetchTemplate(templateId: string): Promise<UserTemplate> {
  const { data } = await client.get(`/templates/${templateId}`);
  return data;
}
