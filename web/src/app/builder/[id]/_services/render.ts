import client from "@/services/client";
import type { SectionInstance, TemplateManifest } from "@/lib/cv/types";
import type { SupportMap } from "../_types/render";

export interface RenderHtmlRequest {
  manifest: TemplateManifest | null;
  cv_sections: SectionInstance[];
  customizations: Record<string, unknown>;
  preview: boolean;
}

export interface RenderHtmlResponse {
  html: string;
}

export async function fetchRendererSupport(): Promise<SupportMap> {
  const { data } = await client.get("/render/support");
  return data as SupportMap;
}

export async function renderHtml(request: RenderHtmlRequest): Promise<RenderHtmlResponse> {
  const { data } = await client.post("/render/html", request);
  return data as RenderHtmlResponse;
}
