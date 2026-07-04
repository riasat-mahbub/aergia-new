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
  is_system: boolean;
  user_id: string | null;
  created_at: string;
}

export async function fetchSystemTemplates(): Promise<UserTemplate[]> {
  const { data } = await client.get("/templates");
  return data;
}

export async function fetchTemplate(templateId: string): Promise<UserTemplate> {
  const { data } = await client.get(`/templates/${templateId}`);
  return data;
}
