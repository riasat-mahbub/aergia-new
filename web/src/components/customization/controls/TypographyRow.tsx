/**
 * TypographyRow — per-field typography row with live mini-preview.
 *
 * This is the signature component of the redesign. Each row owns its
 * own fragment render: the sample text appears below the controls,
 * styled with the current TextStyle. As the user toggles Bold / Italic
 * / Underline / Strikethrough / Size / Color, the preview updates
 * alongside the iframe to the right.
 *
 * Per-field styling writes to `style.text[key]` on the section
 * instance. The resolver reads this and applies via
 * `apply_field_text_styles` (api/app/services/renderer/builders/).
 * Rich-text fields are not styled here — the inspector renders a
 * redirect note and links to the rich-text editor instead.
 *
 * Underline and Strikethrough are newly exposed (the old panel only
 * had Bold/Italic/Size/Color). The schema and renderer already support
 * them — they just weren't surfaced.
 */

import { useMemo } from "react";
import type { TextStyle } from "../../../generated/schema";
import { FONT_SIZE_CSS, FONT_SIZE_LABELS, FONT_SIZE_TOKENS } from "../../../styles/tokens";
import { ink, radius, rule } from "../../../styles/tokens";
import { TEXT_STYLE_DEFAULTS } from "../../../lib/sections/styleDefaults";
import ColorChip from "./ColorChip";

interface Props {
  /** The field key. Used as the label suffix and the write key. */
  label: string;
  /** The current TextStyle for this field (effective, including defaults). */
  current: TextStyle;
  /** Sample text from the user's data — what the preview renders. */
  sample: string;
  /** Called with the new TextStyle when any control changes. */
  onChange: (next: TextStyle) => void;
  /** Hide the typography controls and show a redirect when the field
   * is rich text (the rich-text editor handles per-run styling). */
  isRichText?: boolean;
  testId?: string;
}

export default function TypographyRow({ label, current, sample, onChange, isRichText, testId }: Props) {
  const merged = useMemo<TextStyle>(() => ({ ...TEXT_STYLE_DEFAULTS, ...current }), [current]);

  const set = <K extends keyof TextStyle>(k: K, v: TextStyle[K]) => {
    const next = { ...current, [k]: v };
    // Drop keys that hold the default so the wire stays minimal.
    const cleaned = { ...next };
    if (cleaned[k] === TEXT_STYLE_DEFAULTS[k]) delete cleaned[k];
    onChange(cleaned);
  };

  const toggle = (k: "bold" | "italic" | "underline" | "strike") => {
    set(k, !current[k]);
  };

  if (isRichText) {
    return (
      <div
        className="flex items-center justify-between rounded border px-3 py-2 text-xs"
        style={{ borderColor: rule }}
        data-testid={testId}
      >
        <div>
          <span className="font-medium" style={{ color: ink.ink }}>{label}</span>
          <p className="mt-0.5 text-xs" style={{ color: ink.ink3 }}>
            Rich text field — format inside the content editor.
          </p>
        </div>
      </div>
    );
  }

  const previewStyle: React.CSSProperties = {
    fontWeight: merged.bold ? 700 : 400,
    fontStyle: merged.italic ? "italic" : "normal",
    textDecoration: [
      merged.underline ? "underline" : "",
      merged.strike ? "line-through" : "",
    ].filter(Boolean).join(" ") || undefined,
    color: merged.color ?? ink.ink,
    fontSize: merged.font_size ? FONT_SIZE_CSS[merged.font_size] : undefined,
    fontFamily: "var(--font-ui)",
  };

  return (
    <div
      className="rounded border p-3"
      style={{ borderColor: rule }}
      data-testid={testId}
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: ink.ink3 }}>
          {label}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <ToggleBtn label="B" active={!!merged.bold} onClick={() => toggle("bold")} ariaLabel="Bold" />
        <ToggleBtn label="I" active={!!merged.italic} onClick={() => toggle("italic")} ariaLabel="Italic" style={{ fontStyle: "italic" }} />
        <ToggleBtn
          label={<span style={{ textDecoration: "underline" }}>U</span>}
          active={!!merged.underline}
          onClick={() => toggle("underline")}
          ariaLabel="Underline"
        />
        <ToggleBtn
          label={<span style={{ textDecoration: "line-through" }}>S</span>}
          active={!!merged.strike}
          onClick={() => toggle("strike")}
          ariaLabel="Strikethrough"
        />
        <select
          value={merged.font_size ?? ""}
          onChange={(e) => set("font_size", e.target.value ? (e.target.value as TextStyle["font_size"]) : null)}
          className="rounded border px-2 py-1 text-xs"
          style={{ borderColor: rule }}
          aria-label="Font size"
        >
          <option value="">Default</option>
          {FONT_SIZE_TOKENS.map((tok) => (
            <option key={tok} value={tok}>{FONT_SIZE_LABELS[tok]}</option>
          ))}
        </select>
        <ColorChip
          value={merged.color ?? null}
          onChange={(next) => set("color", next)}
          label={`${label} color`}
        />
      </div>
      <div
        className="mt-3 truncate rounded px-2 py-2"
        style={{
          background: "var(--paper-1)",
          color: ink.ink2,
          borderRadius: radius.r1,
          ...previewStyle,
        }}
        data-testid={testId ? `${testId}-preview` : undefined}
        aria-label={`${label} preview`}
      >
        {sample || label}
      </div>
    </div>
  );
}

function ToggleBtn({
  label,
  active,
  onClick,
  ariaLabel,
  style,
}: {
  label: React.ReactNode;
  active: boolean;
  onClick: () => void;
  ariaLabel: string;
  style?: React.CSSProperties;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={active}
      aria-label={ariaLabel}
      onClick={onClick}
      className="inline-flex h-7 w-7 items-center justify-center rounded text-sm transition-colors"
      style={{
        background: active ? ink.ink : "transparent",
        color: active ? "white" : ink.ink,
        border: `1px solid ${rule}`,
        borderRadius: radius.r1,
        ...style,
      }}
    >
      {label}
    </button>
  );
}
