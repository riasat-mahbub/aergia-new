/**
 * SectionMiniPreview — a tiny rendering of the section's content with
 * current styles applied.
 *
 * The header of every section card in the inspector. Updates live on
 * every change. Anchors the user to *what they're editing*: the
 * preview shows the actual section content with the resolved font
 * family, accent color, and section color applied.
 *
 * Implementation note: this is intentionally a stripped-down render,
 * not a full AST walk. It shows the title and the first two or three
 * fields, enough to anchor. The full preview lives in the iframe to
 * the right; this is the inspector-side companion.
 */

import { useMemo } from "react";
import type { SectionInstance } from "../../../lib/sections/types";
import { SECTION_LABELS } from "../../../lib/sections/types";
import { fieldsForInstance } from "../../../lib/sections/fieldsForInstance";
import { effectiveStyle } from "../../../lib/sections/cascade";
import { ink, radius, rule } from "../../../styles/tokens";

interface Props {
  instance: SectionInstance;
  /** Resolved document accent — used as the title color. */
  accent: string | null;
  /** Resolved document body font — used for the preview text. */
  bodyFont: string | null;
}

export default function SectionMiniPreview({ instance, accent: accentColor, bodyFont }: Props) {
  const style = useMemo(() => effectiveStyle(instance.type, instance.style), [instance.type, instance.style]);
  const rows = useMemo(() => fieldsForInstance(instance).slice(0, 3), [instance]);

  const titleColor = style.subsection?.section_color ?? accentColor ?? ink.ink;
  const font = bodyFont ?? "var(--font-ui)";

  return (
    <div
      className="flex flex-col gap-1 rounded px-3 py-2"
      style={{
        background: "var(--paper-1)",
        borderRadius: radius.r1,
        border: `1px solid ${rule}`,
      }}
      aria-label={`${instance.title} preview`}
    >
      <div className="flex items-baseline gap-2">
        <span
          className="text-sm font-semibold"
          style={{ color: titleColor, fontFamily: font }}
        >
          {instance.title}
        </span>
        <span className="text-[10px] uppercase tracking-wide" style={{ color: ink.ink3 }}>
          {SECTION_LABELS[instance.type] || instance.type}
        </span>
      </div>
      {rows.map((r) => (
        <div
          key={r.key}
          className="truncate text-xs"
          style={{ color: ink.ink2, fontFamily: font }}
        >
          <span className="font-medium">{r.label}:</span> {r.sample}
        </div>
      ))}
      {rows.length === 0 && (
        <div className="text-xs" style={{ color: ink.ink3 }}>No fields yet.</div>
      )}
    </div>
  );
}
