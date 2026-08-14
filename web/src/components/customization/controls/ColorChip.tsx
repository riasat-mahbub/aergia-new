/**
 * ColorChip — swatch + hex inline editor.
 *
 * Replaces the four near-duplicate color controls the old panel had
 * (Document accent, Block style section_color, Block style background_color,
 * Field style color). One component, one idiom.
 *
 * Behavior:
 * - The swatch shows the current value or a hairline placeholder when
 *   the value is unset.
 * - The hex input is editable; clearing it sets the value to null
 *   (which means "inherit" — the resolver falls back to the type /
 *   document default).
 * - Invalid hex strings (anything that doesn't match /^#[0-9a-fA-F]{6}$/)
 *   are kept as-is in the input so the user can keep typing, but the
 *   swatch falls back to a neutral until the string becomes valid.
 * - Pressing Enter or blurring commits the value.
 */

import { useState } from "react";
import { X } from "lucide-react";
import { ink, radius, ruleDefault } from "../../../styles/tokens";

const HEX_RE = /^#[0-9a-fA-F]{6}$/;

interface Props {
  value: string | null | undefined;
  onChange: (next: string | null) => void;
  /** Optional small "X" revert affordance — shows when an inherited
   * default exists and the user has overridden it. Clicking sets the
   * value to null. */
  showRevert?: boolean;
  onRevert?: () => void;
  /** Optional label shown to screen readers and as a placeholder. */
  label?: string;
  /** Test id passthrough for unit tests. */
  testId?: string;
}

export default function ColorChip({ value, onChange, showRevert, onRevert, label, testId }: Props) {
  const [draft, setDraft] = useState<string>(value ?? "");
  const valid = typeof value === "string" && HEX_RE.test(value);

  const commit = (next: string) => {
    setDraft(next);
    if (next === "") {
      onChange(null);
      return;
    }
    if (HEX_RE.test(next)) onChange(next);
    // Invalid strings: keep the draft locally but don't propagate —
    // the resolver would reject anything non-hex anyway.
  };

  return (
    <div
      className="flex items-center gap-2"
      data-testid={testId}
      style={{ borderColor: ruleDefault, borderRadius: radius.r1 }}
    >
      <label
        className="relative inline-flex h-7 w-9 cursor-pointer items-center justify-center overflow-hidden rounded border"
        style={{ borderColor: ruleDefault }}
        title={label ?? "Color"}
      >
        <input
          type="color"
          value={valid && typeof value === "string" ? value : "#000000"}
          onChange={(e) => commit(e.target.value)}
          className="absolute inset-0 h-full w-full cursor-pointer border-0 bg-transparent p-0"
          aria-label={label ?? "Color"}
        />
        <span
          className="pointer-events-none h-5 w-5 rounded-sm"
          style={{
            background: valid && typeof value === "string" ? value : "transparent",
            border: valid ? "none" : `1px dashed ${ink.ink3}`,
          }}
        />
      </label>
      <input
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={(e) => commit(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") commit((e.target as HTMLInputElement).value); }}
        placeholder="#RRGGBB"
        className="w-24 rounded border px-2 py-1 font-mono text-xs"
        style={{ borderColor: ruleDefault }}
        aria-label={label ? `${label} hex` : "Hex value"}
      />
      {showRevert && onRevert && (
        <button
          type="button"
          onClick={onRevert}
          className="inline-flex h-6 w-6 items-center justify-center rounded text-xs"
          style={{ color: ink.ink3 }}
          aria-label="Revert to inherited"
          title="Revert to inherited"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
