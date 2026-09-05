/** Pure CV month parsing and display formatting. */

import type { DateStyle } from "./schema";

export type DateStyleKey = Exclude<DateStyle["key"], undefined>;

export const DATE_STYLE_OPTIONS: ReadonlyArray<{
  value: DateStyleKey;
  label: string;
  rangeSep: string;
}> = [
  { value: "YYYY-MM", label: "YYYY-MM", rangeSep: " – " },
  { value: "YYYY/MM", label: "YYYY/MM", rangeSep: "/" },
  { value: "MM/YYYY", label: "MM/YYYY", rangeSep: "/" },
  { value: "MM-YYYY", label: "MM-YYYY", rangeSep: "-" },
  { value: "MM.YYYY", label: "MM.YYYY", rangeSep: "." },
  { value: "YYYY.MM", label: "YYYY.MM", rangeSep: "." },
  { value: "Mon YYYY", label: "Mon YYYY (e.g. Mar 2021)", rangeSep: " – " },
  { value: "Month YYYY", label: "Month YYYY (default; e.g. March 2021)", rangeSep: " – " },
  { value: "YYYY", label: "YYYY", rangeSep: " – " },
  { value: "Mon-YYYY", label: "Mon-YYYY (e.g. Mar-2021)", rangeSep: "-" },
];

const SHORT_MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

/** Parse a `YYYY-MM` string into a Date set to the first of that month. */
export function parseValueToDate(value: string | null | undefined): Date | undefined {
  if (!value) return undefined;
  const [yearValue, monthValue] = value.split("-");
  if (!yearValue || !monthValue) return undefined;
  const year = Number(yearValue);
  const month = Number(monthValue);
  if (!Number.isInteger(year) || !Number.isInteger(month)) return undefined;
  if (month < 1 || month > 12) return undefined;
  return new Date(year, month - 1, 1);
}

/** Format a Date as `YYYY-MM` using local time. */
export function formatDateToValue(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

export function formatDisplayDate(value: string | null | undefined): string {
  const date = parseValueToDate(value);
  if (!date) return "";
  return `${MONTH_NAMES[date.getMonth()]} ${date.getFullYear()}`;
}

/** Format a single month value according to the selected display style. */
export function formatSingleDate(
  value: string | null | undefined,
  style?: DateStyle | null,
): string {
  if (!value) return "";
  if (!style || !style.key) return value;
  const date = parseValueToDate(value);
  if (!date) return value;

  const year = String(date.getFullYear());
  const month = date.getMonth();
  const paddedMonth = String(month + 1).padStart(2, "0");
  switch (style.key) {
    case "YYYY-MM": return `${year}-${paddedMonth}`;
    case "YYYY/MM": return `${year}/${paddedMonth}`;
    case "MM/YYYY": return `${paddedMonth}/${year}`;
    case "MM-YYYY": return `${paddedMonth}-${year}`;
    case "MM.YYYY": return `${paddedMonth}.${year}`;
    case "YYYY.MM": return `${year}.${paddedMonth}`;
    case "Mon YYYY": return `${SHORT_MONTH_NAMES[month]} ${year}`;
    case "Month YYYY": return `${MONTH_NAMES[month]} ${year}`;
    case "YYYY": return year;
    case "Mon-YYYY": return `${SHORT_MONTH_NAMES[month]}-${year}`;
    default: return value;
  }
}

export function formatDateRange(
  start: string,
  end: string | null,
  current: boolean,
  style?: DateStyle | null,
): string {
  if (!start) return "";
  if (current) return `${formatSingleDate(start, style)} – Present`;
  if (!end) return formatSingleDate(start, style);
  return `${formatSingleDate(start, style)}${style?.rangeSep ?? " – "}${formatSingleDate(end, style)}`;
}
