import client from "./client";
import type { SectionInstance } from "../sections/types";
import {
  loadKeys,
  pickActiveProvider,
  type LLMProviderKey,
} from "../llm/keys";

export interface ParseConfidence {
  path: (string | number)[];
  level: "high" | "medium" | "low";
}

export interface ParseReport {
  fields: ParseConfidence[];
  overall_level: "high" | "medium" | "low";
}

export interface ParseMeta {
  source: "regex" | "llm";
  warnings: string[];
}

export interface ParseResult {
  sections: SectionInstance[];
  confidence: ParseReport;
  meta: ParseMeta;
}

/**
 * Upload a PDF for parsing. Returns a `ParseResult` whose `sections`
 * are the importable `SectionInstance[]` shape ready for the existing
 * CV builder UI. No persistence happens here — the user saves via the
 * normal `POST /api/v1/cvs` flow.
 *
 * When a key for one of the four supported providers is stored in
 * `sessionStorage` (see `web/src/lib/llm/keys.ts`), the matching
 * (provider, api_key) pair is sent as multipart form fields. If no
 * key is set, the orchestrator runs the existing regex path.
 *
 * Timeout widened to 120s from 60s because LLM calls typically take
 * 5-30s on top of the existing 60s budget for PDF extraction.
 */
export async function importPDF(file: File): Promise<ParseResult> {
  const fd = new FormData();
  fd.append("file", file);
  const keys = loadKeys();
  const provider: LLMProviderKey | null = pickActiveProvider(keys);
  if (provider) {
    const key = keys[provider];
    if (key) {
      fd.append("provider", provider);
      fd.append("api_key", key);
    }
  }
  const { data } = await client.post("/cvs/import/pdf", fd, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120_000,
  });
  return data as ParseResult;
}
