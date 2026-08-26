/**
 * OverridePill — small inline indicator on document controls when a
 * per-section override exists.
 *
 * Replaces the silent cascade behavior the old panel had: the user
 * could set a document accent and then set a per-instance section_color
 * and have no idea the document value was being overridden for that
 * section. Now the document control shows "1 section overrides" with
 * a clickable chip that scrolls to (and selects) that section.
 *
 * The chip is purely informational when collapsed; clicking it invokes
 * the callback (the inspector parent scrolls the section card into
 * view and selects it).
 */

import { accent, accentSoft, radius } from "../../../styles/tokens";

interface Props {
  /** Human-readable list of section titles that override this control. */
  sections: string[];
  /** Called when the user clicks the chip. */
  onJump: () => void;
}

export default function OverridePill({ sections, onJump }: Props) {
  if (sections.length === 0) return null;
  const label = sections.length === 1
    ? `1 section overrides`
    : `${sections.length} sections override`;
  return (
    <button
      type="button"
      onClick={onJump}
      className="ml-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs"
      style={{
        background: accentSoft,
        color: accent.accent,
        borderRadius: radius.pill,
      }}
      title={`${label}: ${sections.join(", ")}`}
    >
      {label}
    </button>
  );
}
