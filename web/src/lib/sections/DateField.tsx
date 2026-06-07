import { useEffect, useId, useRef, useState } from "react";
import { DayPicker } from "react-day-picker";
import { Calendar, X } from "lucide-react";

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
 */
export function formatDateRange(start: string, end: string | null, current: boolean): string {
  if (!start) return "";
  if (current) return `${start} – Present`;
  if (!end) return start;
  return `${start} – ${end}`;
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

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function formatDisplay(value: string | null | undefined): string {
  const d = parseValueToDate(value);
  if (!d) return "";
  return `${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`;
}

export default function DateField({
  value,
  onChange,
  label,
  disabled,
  placeholder,
}: DateFieldProps) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverId = useId();

  const selected = parseValueToDate(value);
  const display = formatDisplay(value);
  const showClear = !!value && !disabled;

  // Year range: 1950 → current+10. Plenty of headroom for birth years and
  // forward planning, without bloating the dropdown.
  const currentYear = new Date().getFullYear();
  const startMonth = new Date(1950, 0, 1);
  const endMonth = new Date(currentYear + 10, 11, 31);

  // Close on outside click and on Escape.
  useEffect(() => {
    if (!open) return;
    const onPointer = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
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

  return (
    <div>
      {label && (
        <label className="block text-xs text-gray-500" htmlFor={popoverId}>
          {label}
        </label>
      )}
      <div ref={wrapRef} className="relative mt-0.5">
        <div
          data-testid="datefield"
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
        {open && !disabled && (
          <div
            role="dialog"
            aria-label={label ? `Pick ${label.toLowerCase()}` : "Pick date"}
            className="absolute left-0 top-full z-50 mt-1 rounded-md border border-gray-200 bg-white p-2 shadow-lg"
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
        )}
      </div>
    </div>
  );
}
