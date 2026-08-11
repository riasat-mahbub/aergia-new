/**
 * TokenPicker — 3- or 5-bucket radio chip group with an optional gap
 * indicator.
 *
 * Replaces the spacing radios at the document level (compact /
 * comfortable / minimal — 3 buckets) AND the raw pixel text inputs at
 * the section level (spacing_before / spacing_after — also collapsed
 * into tokens). One component, one idiom.
 *
 * The gap indicator renders the resolved px value as a thin colored
 * bar so the user sees the spacing they're picking. The bar is a
 * visual hint, not an exact representation — Chromium rounds to 1px.
 */

import { SECTION_SPACING_LABELS, SECTION_SPACING_TOKENS, SECTION_SPACING_PX } from "../../../styles/tokens";
import { ink, radius, rule } from "../../../styles/tokens";
import type { SectionSpacingToken } from "../../../styles/tokens";

interface Props {
  /** The currently selected token. `null` means "inherit from template". */
  value: SectionSpacingToken | null;
  onChange: (next: SectionSpacingToken | null) => void;
  /** Show the "Default" pill — when true, the user can clear back to
   * the inherited value. */
  showDefault?: boolean;
  /** Show the gap indicator on the right of the picker. */
  showIndicator?: boolean;
  /** Label shown above the picker. */
  label?: string;
  testId?: string;
}

export default function TokenPicker({
  value,
  onChange,
  showDefault = true,
  showIndicator = true,
  label,
  testId,
}: Props) {
  const selected = value ?? null;
  const indicatorPx = selected ? SECTION_SPACING_PX[selected] : 0;

  return (
    <div className="flex items-center gap-3" data-testid={testId}>
      {label && (
        <span className="w-24 text-xs" style={{ color: ink.ink3 }}>{label}</span>
      )}
      <div
        className="flex flex-wrap items-center gap-1.5 rounded p-1"
        style={{ borderColor: rule, borderWidth: 1, borderStyle: "solid" }}
        role="radiogroup"
        aria-label={label}
      >
        {showDefault && (
          <TokenChip
            label="Default"
            active={selected === null}
            onClick={() => onChange(null)}
          />
        )}
        {SECTION_SPACING_TOKENS.map((tok) => (
          <TokenChip
            key={tok}
            label={SECTION_SPACING_LABELS[tok]}
            active={selected === tok}
            onClick={() => onChange(tok)}
          />
        ))}
      </div>
      {showIndicator && (
        <div
          className="flex items-center"
          title={`${indicatorPx}px gap`}
          aria-label={`${indicatorPx}px gap indicator`}
        >
          <span
            className="rounded-sm"
            style={{
              width: Math.max(2, indicatorPx / 2),
              height: 8,
              background: selected ? ink.ink : ink.ink4,
              borderRadius: radius.r1,
              transition: "width 120ms cubic-bezier(0.23, 1, 0.32, 1)",
            }}
          />
        </div>
      )}
    </div>
  );
}

function TokenChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={active}
      onClick={onClick}
      className="rounded px-2 py-0.5 text-xs transition-colors"
      style={{
        background: active ? ink.ink : "transparent",
        color: active ? "white" : ink.ink2,
        borderRadius: radius.r1,
      }}
    >
      {label}
    </button>
  );
}
