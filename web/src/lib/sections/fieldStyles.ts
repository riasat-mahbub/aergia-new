export interface FieldDef {
  key: string;
  label: string;
}

export const FIELD_DEFS: Record<string, FieldDef[]> = {
  profile: [{ key: "name", label: "Name" }, { key: "title", label: "Title" }, { key: "email", label: "Email" }, { key: "phone", label: "Phone" }, { key: "location", label: "Location" }, { key: "site", label: "Site" }, { key: "social_links", label: "Social Links" }, { key: "summary", label: "Summary" }],
  experience: [{ key: "position", label: "Position" }, { key: "company", label: "Company" }, { key: "date", label: "Date" }, { key: "description", label: "Description" }],
  education: [{ key: "degree", label: "Degree" }, { key: "institution", label: "Institution" }, { key: "date", label: "Date" }, { key: "gpa", label: "GPA" }, { key: "summary", label: "Summary" }],
  projects: [{ key: "project", label: "Name" }, { key: "link", label: "Link" }, { key: "date", label: "Date" }, { key: "description", label: "Description" }, { key: "tech", label: "Tech" }],
  skills: [{ key: "category", label: "Category" }, { key: "tag", label: "Skill tag" }],
  certifications: [{ key: "certification", label: "Name" }, { key: "issuer", label: "Issuer" }, { key: "date", label: "Date" }, { key: "link", label: "Credential link" }],
  research: [{ key: "paper", label: "Paper title" }, { key: "venue", label: "Venue" }, { key: "link", label: "Paper link" }, { key: "date", label: "Publication date" }, { key: "description", label: "Description" }],
};

export function getFieldDefs(sectionType: string): FieldDef[] {
  return FIELD_DEFS[sectionType] || [];
}
