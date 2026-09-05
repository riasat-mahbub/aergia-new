import type { TemplateManifest } from "@/shared/cv/schema";

export interface UserTemplate {
  id: string;
  name: string;
  description: string | null;
  preview_image_url: string | null;
  manifest: TemplateManifest | null;
}
