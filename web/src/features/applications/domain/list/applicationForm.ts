import type {
  Application,
  ApplicationCreateData,
  ApplicationUpdateData,
} from "@/features/applications/types";

export const EMPTY_APPLICATION_FORM = {
  company: "",
  role: "",
  job_description: "",
  job_url: "",
  notes: "",
  next_follow_up_at: "",
};

export type ApplicationFormState = typeof EMPTY_APPLICATION_FORM;

export function formFromApplication(application: Application | null | undefined): ApplicationFormState {
  if (!application) return EMPTY_APPLICATION_FORM;
  return {
    company: application.company,
    role: application.role,
    job_description: application.job_description,
    job_url: application.job_url ?? "",
    notes: application.notes ?? "",
    next_follow_up_at: application.next_follow_up_at ?? "",
  };
}

export function requiredApplicationFields(form: ApplicationFormState) {
  return {
    company: form.company.trim(),
    role: form.role.trim(),
    jobDescription: form.job_description.trim(),
  };
}

export function validateApplicationForm(form: ApplicationFormState): string | null {
  const { company, role, jobDescription } = requiredApplicationFields(form);
  return company && role && jobDescription ? null : "Company, Role, and Job description are required.";
}

export function createDataFromForm(form: ApplicationFormState): ApplicationCreateData {
  const { company, role, jobDescription } = requiredApplicationFields(form);
  return {
    company,
    role,
    job_description: jobDescription,
    job_url: form.job_url.trim() || undefined,
    notes: form.notes.trim() || undefined,
    ...(form.next_follow_up_at ? { next_follow_up_at: form.next_follow_up_at } : {}),
  };
}

export function updateDataFromForm(form: ApplicationFormState): ApplicationUpdateData {
  const { company, role, jobDescription } = requiredApplicationFields(form);
  return {
    company,
    role,
    job_description: jobDescription,
    job_url: form.job_url.trim() || null,
    notes: form.notes.trim() || null,
    next_follow_up_at: form.next_follow_up_at || null,
  };
}

export function applicationSaveError(_error: unknown): string {
  return "Unable to save this application. Please try again.";
}
