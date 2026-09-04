import type { TemplateManifest } from "@/lib/sections/types";

export interface UserTemplate {
  id: string;
  name: string;
  description: string | null;
  preview_image_url: string | null;
  manifest: TemplateManifest | null;
}
