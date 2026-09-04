import client from "./client";
import type { SupportMap } from "@/contracts/render";

export async function fetchRendererSupport(): Promise<SupportMap> {
  const { data } = await client.get("/render/support");
  return data as SupportMap;
}
