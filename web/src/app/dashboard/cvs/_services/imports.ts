import client from "@/services/client";
import type { ParseResult } from "../_types/imports";
import type { LLMProviderKey } from "@/contracts/llm";

/**
 * Upload a PDF for parsing. Returns a `ParseResult` whose `sections`
 * are the importable `SectionInstance[]` shape ready for the existing
 * CV builder UI. No persistence happens here — the user saves via the
 * normal `POST /api/v1/cvs` flow.
 *
 * When explicit provider credentials are supplied, the matching
 * (provider, api_key) pair is sent as multipart form fields. If no
 * credentials are supplied, the orchestrator runs the existing regex path.
 *
 * Timeout widened to 120s from 60s because LLM calls typically take
 * 5-30s on top of the existing 60s budget for PDF extraction.
 */
export interface ImportCredentials {
  provider: LLMProviderKey;
  apiKey: string;
}

export async function importPDF(file: File, credentials?: ImportCredentials): Promise<ParseResult> {
  const fd = new FormData();
  fd.append("file", file);
  if (credentials?.apiKey.trim()) {
    fd.append("provider", credentials.provider);
    fd.append("api_key", credentials.apiKey);
  }
  const { data } = await client.post("/cvs/import/pdf", fd, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120_000,
  });
  return data as ParseResult;
}
