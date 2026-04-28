import type { SectionInstance } from "../sections/types";
import {
  profileSchema,
  experienceEntrySchema,
  educationEntrySchema,
  skillGroupSchema,
  projectEntrySchema,
  languageEntrySchema,
  certificationEntrySchema,
} from "./sections";

type Errors = Record<string, string>;

const ARRAY_SECTION_SCHEMAS: Record<string, any> = {
  experience: experienceEntrySchema,
  education: educationEntrySchema,
  skills: skillGroupSchema,
  projects: projectEntrySchema,
  languages: languageEntrySchema,
  certifications: certificationEntrySchema,
};

export function validateSection(instance: SectionInstance): Errors {
  const { type, data } = instance;
  if (!data) return {};

  if (type === "profile") {
    const result = profileSchema.safeParse(data);
    if (!result.success) {
      return formatErrors(result.error.errors);
    }
    return {};
  }

  const schema = ARRAY_SECTION_SCHEMAS[type];
  if (schema && Array.isArray(data)) {
    const errors: Errors = {};
    data.forEach((entry: unknown, i: number) => {
      const result = schema.safeParse(entry);
      if (!result.success) {
        const fieldErrors = formatErrors(result.error.errors);
        for (const [key, val] of Object.entries(fieldErrors)) {
          errors[`${i}.${key}`] = val;
        }
      }
    });
    return errors;
  }

  return {};
}

function formatErrors(errors: { path: (string | number)[]; message: string }[]): Errors {
  const result: Errors = {};
  for (const err of errors) {
    const key = err.path.join(".");
    if (!result[key]) {
      result[key] = err.message;
    }
  }
  return result;
}
