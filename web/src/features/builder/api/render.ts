import client from "@/shared/api/client";
import type { RenderHtmlRequest, RenderHtmlResponse, SupportMap } from "../types/render";

export async function fetchRendererSupport(): Promise<SupportMap> {
  const { data } = await client.get("/render/support");
  return data as SupportMap;
}

export async function renderHtml(request: RenderHtmlRequest): Promise<RenderHtmlResponse> {
  const { data } = await client.post("/render/html", request);
  return data as RenderHtmlResponse;
}
