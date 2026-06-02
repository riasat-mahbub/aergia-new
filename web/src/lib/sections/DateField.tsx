import { X } from "lucide-react";

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

export default function DateField({
  value,
  onChange,
  label,
  disabled,
  placeholder,
}: DateFieldProps) {
  const display = value ?? "";
  const showClear = !!display && !disabled;

  return (
    <div>
      {label && <label className="block text-xs text-gray-500">{label}</label>}
      <div className="relative mt-0.5">
        <input
          type="month"
          value={display}
          onChange={(e) => onChange(e.target.value || null)}
          disabled={disabled}
          placeholder={placeholder}
          aria-label={label}
          className="w-full rounded border px-2 py-1 text-sm disabled:opacity-50"
        />
        {showClear && (
          <button
            type="button"
            onClick={() => onChange("")}
            aria-label="Clear"
            className="absolute right-1 top-1/2 -translate-y-1/2 rounded p-1 text-gray-400 hover:text-gray-600"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}
