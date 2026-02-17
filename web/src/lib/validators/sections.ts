import { z } from "zod";

export const profileSchema = z.object({
  name: z.string().min(1, "Name is required"),
  title: z.string().min(1, "Title is required"),
  email: z.string().email("Invalid email address"),
  phone: z.string().min(1, "Phone is required"),
  location: z.string().min(1, "Location is required"),
  summary: z.string().min(1, "Summary is required"),
  photo_url: z.string(),
});

export const experienceEntrySchema = z.object({
  id: z.string().min(1),
  company: z.string().min(1, "Company is required"),
  position: z.string().min(1, "Position is required"),
  start_date: z.string().min(1, "Start date is required"),
  end_date: z.string().nullable(),
  current: z.boolean(),
  location: z.string().min(1, "Location is required"),
  description: z.string().min(1, "Description is required"),
});

export const educationEntrySchema = z.object({
  id: z.string().min(1),
  institution: z.string().min(1, "Institution is required"),
  degree: z.string().min(1, "Degree is required"),
  start_date: z.string().min(1, "Start date is required"),
  end_date: z.string().nullable(),
  current: z.boolean(),
  gpa: z.string(),
});

export const skillGroupSchema = z.object({
  id: z.string().min(1),
  category: z.string().min(1, "Category is required"),
  items: z.array(z.string()),
});

export const projectEntrySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1, "Name is required"),
  url: z.string(),
  start_date: z.string().min(1, "Start date is required"),
  end_date: z.string().nullable(),
  description: z.string().min(1, "Description is required"),
  tech_stack: z.array(z.string()),
});

export const languageEntrySchema = z.object({
  id: z.string().min(1),
  language: z.string().min(1, "Language is required"),
  proficiency: z.string().min(1, "Proficiency is required"),
});

export const certificationEntrySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1, "Name is required"),
  issuer: z.string().min(1, "Issuer is required"),
  date: z.string(),
  credential_url: z.string(),
});

export const sectionDataSchema = z.object({
  profile: profileSchema.optional(),
  experience: z.array(experienceEntrySchema).optional(),
  education: z.array(educationEntrySchema).optional(),
  skills: z.array(skillGroupSchema).optional(),
  projects: z.array(projectEntrySchema).optional(),
  languages: z.array(languageEntrySchema).optional(),
  certifications: z.array(certificationEntrySchema).optional(),
});

export const cvSectionsSchema = z.object({
  order: z.array(z.string()),
  enabled: z.array(z.string()),
  data: sectionDataSchema,
});

export type ProfileData = z.infer<typeof profileSchema>;
export type ExperienceEntry = z.infer<typeof experienceEntrySchema>;
export type EducationEntry = z.infer<typeof educationEntrySchema>;
export type SkillGroup = z.infer<typeof skillGroupSchema>;
export type ProjectEntry = z.infer<typeof projectEntrySchema>;
export type LanguageEntry = z.infer<typeof languageEntrySchema>;
export type CertificationEntry = z.infer<typeof certificationEntrySchema>;
export type SectionData = z.infer<typeof sectionDataSchema>;
export type CVSections = z.infer<typeof cvSectionsSchema>;
