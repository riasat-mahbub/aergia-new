import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { DayPicker } from "react-day-picker";
import { Calendar, X } from "lucide-react";
import type { DateStyle, DateStyleKey } from "./types";

interface DateFieldProps {
  value: string | null;
  onChange: (v: string | null) => void;
  label?: string;
  disabled?: boolean;
  placeholder?: string;
}

/**
 * Format a date range for display.
 * - Empty start → empty string
 * - Empty end + current=false → just "start"
 * - Empty end + current=true → "start – Present"
 * - Both set → "start – end"
 * - current=true takes precedence over any end value
 * - When `style` is set, each bound is first reformatted via formatSingleDate
 *   and the range is joined with `style.rangeSep`. The default behavior
 *   (no style) is unchanged.
 */
export function formatDateRange(
  start: string,
  end: string | null,
  current: boolean,
  style?: DateStyle | null,
): string {
  if (!start) return "";
  if (current) return `${formatSingleDate(start, style)} – Present`;
  if (!end) return formatSingleDate(start, style);
  const a = formatSingleDate(start, style);
  const b = formatSingleDate(end, style);
  return `${a}${style?.rangeSep ?? " – "}${b}`;
}

export const DATE_STYLE_OPTIONS: ReadonlyArray<{
  value: DateStyleKey;
  label: string;
  rangeSep: string;
}> = [
  { value: "YYYY-MM", label: "YYYY-MM (default)", rangeSep: " – " },
  { value: "YYYY/MM", label: "YYYY/MM", rangeSep: "/" },
  { value: "MM/YYYY", label: "MM/YYYY", rangeSep: "/" },
  { value: "MM-YYYY", label: "MM-YYYY", rangeSep: "-" },
  { value: "MM.YYYY", label: "MM.YYYY", rangeSep: "." },
  { value: "YYYY.MM", label: "YYYY.MM", rangeSep: "." },
  { value: "Mon YYYY", label: "Mon YYYY (e.g. Mar 2021)", rangeSep: " – " },
  { value: "Month YYYY", label: "Month YYYY (e.g. March 2021)", rangeSep: " – " },
  { value: "YYYY", label: "YYYY", rangeSep: " – " },
  { value: "Mon-YYYY", label: "Mon-YYYY (e.g. Mar-2021)", rangeSep: "-" },
];

/**
 * Format a single "YYYY-MM" date string for display using the given style.
 *
 * - Empty input → ""
 * - Unparseable input (e.g. legacy year-only "2020", out-of-range months) → raw value
 * - Unset/empty style → raw value
 * - Otherwise switches on style.key
 */
export function formatSingleDate(
  value: string | null | undefined,
  style?: DateStyle | null,
): string {
  if (!value) return "";
  if (!style || !style.key) return value;
  const d = parseValueToDate(value);
  if (!d) return value;
  const year = d.getFullYear();
  const month = d.getMonth();
  const yy = String(year);
  const mm = String(month + 1).padStart(2, "0");
  switch (style.key) {
    case "YYYY-MM":
      return `${yy}-${mm}`;
    case "YYYY/MM":
      return `${yy}/${mm}`;
    case "MM/YYYY":
      return `${mm}/${yy}`;
    case "MM-YYYY":
      return `${mm}-${yy}`;
    case "MM.YYYY":
      return `${mm}.${yy}`;
    case "YYYY.MM":
      return `${yy}.${mm}`;
    case "Mon YYYY":
      return `${SHORT_MONTH_NAMES[month]} ${yy}`;
    case "Month YYYY":
      return `${MONTH_NAMES[month]} ${yy}`;
    case "YYYY":
      return `${yy}`;
    case "Mon-YYYY":
      return `${SHORT_MONTH_NAMES[month]}-${yy}`;
    default:
      return value;
  }
}


/** Parse a "YYYY-MM" string into a Date set to the first of that month. */
function parseValueToDate(value: string | null | undefined): Date | undefined {
  if (!value) return undefined;
  const [y, m] = value.split("-");
  if (!y || !m) return undefined;
  const year = Number(y);
  const month = Number(m);
  if (!Number.isInteger(year) || !Number.isInteger(month)) return undefined;
  if (month < 1 || month > 12) return undefined;
  return new Date(year, month - 1, 1);
}

/** Format a Date as "YYYY-MM" using local time (matches the existing data model). */
function formatDateToValue(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

const SHORT_MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function formatDisplay(value: string | null | undefined): string {
  const d = parseValueToDate(value);
  if (!d) return "";
  return `${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`;
}

const POPOVER_WIDTH = 280; // approximate; read from the rendered element if available
const POPOVER_GAP = 4;

export default function DateField({
  value,
  onChange,
  label,
  disabled,
  placeholder,
}: DateFieldProps) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const popoverId = useId();

  const selected = parseValueToDate(value);
  const display = formatDisplay(value);
  const showClear = !!value && !disabled;

  // Year range: 1950 → current+10. Plenty of headroom for birth years and
  // forward planning, without bloating the dropdown.
  const currentYear = new Date().getFullYear();
  const startMonth = new Date(1950, 0, 1);
  const endMonth = new Date(currentYear + 10, 11, 31);

  // Position the popover relative to the trigger using fixed-position math,
  // so it escapes any ancestor with overflow:hidden (e.g. the accordion body).
  const updatePosition = () => {
    const trigger = triggerRef.current;
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const popover = popoverRef.current;
    const width = popover?.offsetWidth || POPOVER_WIDTH;
    const height = popover?.offsetHeight || 320;
    const margin = 8;
    // Prefer below the trigger, flip above if it would overflow the viewport.
    let top = rect.bottom + POPOVER_GAP;
    if (top + height + margin > window.innerHeight) {
      top = Math.max(margin, rect.top - height - POPOVER_GAP);
    }
    // Center horizontally on the trigger, then clamp to the viewport.
    let left = rect.left + rect.width / 2 - width / 2;
    left = Math.max(margin, Math.min(left, window.innerWidth - width - margin));
    setPos({ top, left });
  };

  // Position before paint so the popover doesn't flash at 0,0.
  useLayoutEffect(() => {
    if (!open) return;
    updatePosition();
  }, [open]);

  // Outside click, Escape, and scroll/resize all close the popover.
  // (Re-positioning on scroll is jarring inside a scrollable section; closing
  // is the more predictable behavior and matches native date inputs.)
  useEffect(() => {
    if (!open) return;
    const onPointer = (e: MouseEvent) => {
      const target = e.target as Node;
      if (triggerRef.current?.contains(target)) return;
      if (popoverRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    const onResize = () => setOpen(false);
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    // Capture phase catches scroll events on any ancestor, not just window.
    document.addEventListener("scroll", onResize, true);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("scroll", onResize, true);
    };
  }, [open]);

  const handleSelect = (day: Date | undefined) => {
    if (!day) {
      onChange(null);
      return;
    }
    const next = formatDateToValue(day);
    if (next !== (value || "")) onChange(next);
    setOpen(false);
    triggerRef.current?.focus();
  };

  const clear = () => {
    onChange("");
    setOpen(false);
    triggerRef.current?.focus();
  };

  const popover = open && !disabled && pos ? (
    <div
      ref={popoverRef}
      role="dialog"
      aria-label={label ? `Pick ${label.toLowerCase()}` : "Pick date"}
      style={{ position: "fixed", top: pos.top, left: pos.left, zIndex: 1000 }}
      className="rounded-md border border-gray-200 bg-white p-2 shadow-lg"
    >
      <DayPicker
        mode="single"
        selected={selected}
        onSelect={handleSelect}
        captionLayout="dropdown"
        startMonth={startMonth}
        endMonth={endMonth}
        hideNavigation
        showOutsideDays
        defaultMonth={selected ?? new Date()}
      />
    </div>
  ) : null;

  return (
    <div>
      {label && (
        <label className="block text-xs text-gray-500" htmlFor={popoverId}>
          {label}
        </label>
      )}
      <div className="mt-0.5">
        <div
          className="flex w-full items-center gap-1 rounded border bg-white text-sm"
        >
          <button
            ref={triggerRef}
            id={popoverId}
            type="button"
            disabled={disabled}
            aria-haspopup="dialog"
            aria-expanded={open}
            aria-label={label || "Date"}
            onClick={() => !disabled && setOpen((o) => !o)}
            className="flex flex-1 items-center gap-1.5 px-2 py-1 text-left disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Calendar aria-hidden="true" className="h-3.5 w-3.5 shrink-0 text-gray-400" />
            <span className={display ? "text-gray-900" : "text-gray-400"}>
              {display || placeholder || "Select month"}
            </span>
          </button>
          {showClear && (
            <button
              type="button"
              onClick={clear}
              aria-label="Clear"
              className="rounded p-1 text-gray-400 hover:text-gray-600"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
      {typeof document !== "undefined" && createPortal(popover, document.body)}
    </div>
  );
}
