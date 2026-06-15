export interface FieldDef {
  key: string;
  label: string;
}

export const FIELD_DEFS: Record<string, FieldDef[]> = {
  profile: [{ key: "name", label: "Name" }, { key: "title", label: "Title" }, { key: "summary", label: "Summary" }, { key: "contact", label: "Contact" }],
  experience: [{ key: "position", label: "Position" }, { key: "company", label: "Company" }, { key: "date", label: "Date" }, { key: "description", label: "Description" }],
  education: [{ key: "degree", label: "Degree" }, { key: "institution", label: "Institution" }, { key: "date", label: "Date" }, { key: "gpa", label: "GPA" }, { key: "summary", label: "Summary" }],
  projects: [{ key: "name", label: "Name" }, { key: "url", label: "Link" }, { key: "date", label: "Date" }, { key: "description", label: "Description" }, { key: "tech", label: "Tech" }],
  skills: [{ key: "category", label: "Category" }, { key: "tag", label: "Skill tag" }],
  certifications: [{ key: "name", label: "Name" }, { key: "meta", label: "Issuer / date" }, { key: "url", label: "Credential link" }],
  research: [{ key: "title", label: "Paper title" }, { key: "url", label: "Paper link" }, { key: "date", label: "Publication date" }, { key: "description", label: "Description" }],
};

export function getFieldDefs(sectionType: string): FieldDef[] {
  return FIELD_DEFS[sectionType] || [];
}
