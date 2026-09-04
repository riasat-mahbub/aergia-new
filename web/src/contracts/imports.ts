import type { SectionInstance } from "@/lib/sections/types";

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
