import client from "./client";

export interface UserTemplate {
  id: string;
  name: string;
  description: string | null;
  preview_image_url: string | null;
  layout_config: Record<string, any>;
  section_schema: Record<string, any>;
  default_customizations: Record<string, any> | null;
  content: string;
  layout_template: string | null;
  manifest: Record<string, any> | null;
  is_user_template: boolean;
  is_system: boolean;
  user_id: string | null;
  created_at: string;
}

export interface UserTemplateCreate {
  name: string;
  description?: string;
  manifest: Record<string, any>;
}

export async function fetchSystemTemplates(): Promise<UserTemplate[]> {
  const { data } = await client.get("/templates");
  return data.filter((t: UserTemplate) => !t.is_user_template);
}

export async function fetchUserTemplates(): Promise<UserTemplate[]> {
  const { data } = await client.get("/templates/user");
  return data;
}

export async function uploadUserTemplate(data: UserTemplateCreate): Promise<UserTemplate> {
  const { data: result } = await client.post("/templates/user", data);
  return result;
}

export async function deleteUserTemplate(templateId: string): Promise<void> {
  await client.delete(`/templates/user/${templateId}`);
}

export async function fetchTemplate(templateId: string): Promise<UserTemplate> {
  const { data } = await client.get(`/templates/${templateId}`);
  return data;
}
