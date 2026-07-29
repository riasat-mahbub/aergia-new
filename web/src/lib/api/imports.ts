import client from "./client";
import type { SectionInstance } from "../sections/types";

export interface ParseConfidence {
  path: (string | number)[];
  level: "high" | "medium" | "low";
}

export interface ParseReport {
  fields: ParseConfidence[];
  overall_level: "high" | "medium" | "low";
}

export interface ParseMeta {
  source: "regex";
  warnings: string[];
}

export interface ParseResult {
  sections: SectionInstance[];
  confidence: ParseReport;
  meta: ParseMeta;
}

/**
 * Upload a PDF for parsing. Returns a `ParseResult` whose `sections` are
 * the importable `SectionInstance[]` shape ready for the existing CV
 * builder UI. No persistence happens here — the user saves via the
 * normal `POST /api/v1/cvs` flow.
 */
export async function importPDF(file: File): Promise<ParseResult> {
  const fd = new FormData();
  fd.append("file", file);
  const { data } = await client.post("/cvs/import/pdf", fd, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60_000,
  });
  return data as ParseResult;
}
