export function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}

export function templateLabel(templateId: string): string {
  return templateId.replace("generic-", "").replace("-", " ");
}
