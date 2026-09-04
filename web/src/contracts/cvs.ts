export interface CVApplicationSummary {
  id: string;
  company: string;
  role: string;
  status: "draft" | "applied" | "responded" | "interview" | "offer" | "hired" | "rejected" | "withdrawn";
  generation_status: "pending" | "ready" | "failed";
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
  customizations: Record<string, unknown>;
  sections: unknown;
  extra_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CVCreateData {
  title: string;
  description?: string;
  template_id?: string;
  sections?: unknown;
  customizations?: Record<string, unknown>;
}

export interface CVUpdateData {
  title?: string;
  description?: string;
  template_id?: string;
  sections?: unknown;
  customizations?: Record<string, unknown>;
}
