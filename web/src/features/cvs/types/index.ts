import type { Customizations, SectionInstance } from "@/shared/cv/schema";

export type CVSections = SectionInstance[];
export type CVCustomizations = Customizations;

export interface CVApplicationSummary {
  id: string;
  company: string;
  role: string;
  status: "draft" | "applied" | "responded" | "interview" | "offer" | "hired" | "rejected" | "withdrawn";
  applied_at: string | null;
}

export interface CVListItem {
  id: string;
  title: string;
  template_id: string;
  created_at: string;
  updated_at: string;
  application?: CVApplicationSummary | null;
}

export interface CVDetail {
  id: string;
  title: string;
  description: string | null;
  template_id: string;
  customizations: CVCustomizations;
  sections: CVSections;
  extra_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CVCreateData {
  title: string;
  description?: string;
  template_id?: string;
  sections?: CVSections;
  customizations?: CVCustomizations;
}

export interface CVUpdateData {
  title?: string;
  description?: string;
  template_id?: string;
  sections?: CVSections;
  customizations?: CVCustomizations;
}
