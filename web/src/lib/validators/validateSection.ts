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

export function validateSection(instance: SectionInstance): Errors {
  const { type, data } = instance;
  if (!data) return {};

  switch (type) {
    case "profile": {
      const result = profileSchema.safeParse(data);
      if (!result.success) {
        return formatErrors(result.error.errors);
      }
      return {};
    }

    case "experience": {
      if (!Array.isArray(data)) return {};
      const errors: Errors = {};
      data.forEach((entry: unknown, i: number) => {
        const result = experienceEntrySchema.safeParse(entry);
        if (!result.success) {
          const fieldErrors = formatErrors(result.error.errors);
          for (const [key, val] of Object.entries(fieldErrors)) {
            errors[`${i}.${key}`] = val;
          }
        }
      });
      return errors;
    }

    case "education": {
      if (!Array.isArray(data)) return {};
      const errors: Errors = {};
      data.forEach((entry: unknown, i: number) => {
        const result = educationEntrySchema.safeParse(entry);
        if (!result.success) {
          const fieldErrors = formatErrors(result.error.errors);
          for (const [key, val] of Object.entries(fieldErrors)) {
            errors[`${i}.${key}`] = val;
          }
        }
      });
      return errors;
    }

    case "skills": {
      if (!Array.isArray(data)) return {};
      const errors: Errors = {};
      data.forEach((entry: unknown, i: number) => {
        const result = skillGroupSchema.safeParse(entry);
        if (!result.success) {
          const fieldErrors = formatErrors(result.error.errors);
          for (const [key, val] of Object.entries(fieldErrors)) {
            errors[`${i}.${key}`] = val;
          }
        }
      });
      return errors;
    }

    case "projects": {
      if (!Array.isArray(data)) return {};
      const errors: Errors = {};
      data.forEach((entry: unknown, i: number) => {
        const result = projectEntrySchema.safeParse(entry);
        if (!result.success) {
          const fieldErrors = formatErrors(result.error.errors);
          for (const [key, val] of Object.entries(fieldErrors)) {
            errors[`${i}.${key}`] = val;
          }
        }
      });
      return errors;
    }

    case "languages": {
      if (!Array.isArray(data)) return {};
      const errors: Errors = {};
      data.forEach((entry: unknown, i: number) => {
        const result = languageEntrySchema.safeParse(entry);
        if (!result.success) {
          const fieldErrors = formatErrors(result.error.errors);
          for (const [key, val] of Object.entries(fieldErrors)) {
            errors[`${i}.${key}`] = val;
          }
        }
      });
      return errors;
    }

    case "certifications": {
      if (!Array.isArray(data)) return {};
      const errors: Errors = {};
      data.forEach((entry: unknown, i: number) => {
        const result = certificationEntrySchema.safeParse(entry);
        if (!result.success) {
          const fieldErrors = formatErrors(result.error.errors);
          for (const [key, val] of Object.entries(fieldErrors)) {
            errors[`${i}.${key}`] = val;
          }
        }
      });
      return errors;
    }

    default:
      return {};
  }
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
