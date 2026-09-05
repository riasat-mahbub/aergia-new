import type { TemplateManifest } from "@/lib/cv/schema";

export interface UserTemplate {
  id: string;
  name: string;
  description: string | null;
  preview_image_url: string | null;
  manifest: TemplateManifest | null;
}
