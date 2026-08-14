/**
 * SectionInspector — per-section card body.
 *
 * Composes the controls primitives into five visual-effect groups:
 *
 *   1. Heading        — show heading toggle, divider toggle, color
 *   2. Spacing        — token picker for space above / below / entries
 *   3. Page break     — start-on-new-page toggle (entry sections only)
 *   4. Alignment      — text align radio chips (disabled for two-column)
 *   5. Typography     — one TypographyRow per actual field
 *
 * Groups are always visible (no disclosure accordion — the inspector
 * is a sidebar, not a settings form). Controls that don't apply to a
 * given section type are hidden. Rich-text fields skip typography with
 * a redirect to the content editor.
 *
 * Writes flow back through onStyleChange(axis, partial) so the parent
 * can persist the new SectionInstanceStyle via onUpdateStyle.
 */

import { useMemo } from "react";
import type {
  LayoutHints,
  SectionInstance,
  SectionPolicy,
  SubsectionStyle,
  TextStyle,
} from "../../generated/schema";
import { fieldsForInstance } from "../../lib/sections/fieldsForInstance";
import { effectiveStyle } from "../../lib/sections/cascade";
import type { SectionInstanceStyle } from "../../lib/sections/types";
import {
  SECTION_SPACING_TOKENS,
  ink,
  radius,
  ruleDefault,
} from "../../styles/tokens";
import type { SectionSpacingToken } from "../../styles/tokens";
import ColorChip from "./controls/ColorChip";
import SectionMiniPreview from "./controls/SectionMiniPreview";
import TokenPicker from "./controls/TokenPicker";
import TypographyRow from "./controls/TypographyRow";

interface Props {
  instance: SectionInstance;
  documentAccent: string | null;
  documentBodyFont: string | null;
  onChange: (next: SectionInstanceStyle) => void;
}

export default function SectionInspector({ instance, documentAccent, documentBodyFont, onChange }: Props) {
  const style = useMemo(() => effectiveStyle(instance.type, instance.style), [instance.type, instance.style]);
  const fields = useMemo(() => fieldsForInstance(instance), [instance]);

  const isProfile = instance.type === "profile";
  const isTwoColumn = style.policy?.entry_layout === "two-column";
  const showTextAlign = !isProfile;
  const showPageBreak = !isProfile;

  const updateSubsection = (partial: Partial<SubsectionStyle>) => {
    const next = { ...style.subsection, ...partial };
    onChange({ ...style, subsection: next });
  };

  const updateLayout = (partial: Partial<LayoutHints>) => {
    const next = { ...style.layout, ...partial };
    onChange({ ...style, layout: next });
  };

  const updatePolicy = (partial: Partial<SectionPolicy>) => {
    const next = { ...style.policy, ...partial };
    onChange({ ...style, policy: next });
  };

  const updateText = (key: string, value: TextStyle | undefined) => {
    const next = { ...style.text };
    if (value === undefined || Object.keys(value).length === 0) {
      delete next[key];
    } else {
      next[key] = value;
    }
    onChange({ ...style, text: next });
  };

  const sectionColorOverridden = !!instance.style?.subsection?.section_color;

  return (
    <div className="space-y-4">
      <SectionMiniPreview instance={instance} accent={documentAccent} bodyFont={documentBodyFont} />

      {/* ── Heading ──────────────────────────────────────────────── */}
      <Group title="Heading">
        {!isProfile && (
          <Row label="Show heading">
            <input
              type="checkbox"
              checked={!!style.policy?.show_title}
              onChange={(e) => updatePolicy({ show_title: e.target.checked })}
              className="h-3.5 w-3.5"
              aria-label="Show heading"
            />
          </Row>
        )}
        {!isProfile && (
          <Row label="Underline heading">
            <input
              type="checkbox"
              checked={!!style.policy?.heading_divider}
              onChange={(e) => updatePolicy({ heading_divider: e.target.checked })}
              className="h-3.5 w-3.5"
              aria-label="Underline heading"
            />
          </Row>
        )}
        <Row label="Heading & text color">
          <ColorChip
            value={style.subsection?.section_color ?? null}
            onChange={(next) => updateSubsection({ section_color: next })}
            label="Heading and text color"
            showRevert={sectionColorOverridden && !!documentAccent}
            onRevert={() => updateSubsection({ section_color: null })}
          />
          {sectionColorOverridden && documentAccent && (
            <span className="ml-2 text-xs" style={{ color: ink.ink3 }}>
              Overrides document accent
            </span>
          )}
        </Row>
      </Group>

      {/* ── Spacing ──────────────────────────────────────────────── */}
      <Group title="Spacing">
        <TokenPicker
          label="Above"
          value={spacingTokenToSpacingToken(style.subsection?.spacing_before)}
          onChange={(tok) => updateSubsection({ spacing_before: tok })}
          testId={`spacing-above-${instance.id}`}
        />
        <TokenPicker
          label="Below"
          value={spacingTokenToSpacingToken(style.subsection?.spacing_after)}
          onChange={(tok) => updateSubsection({ spacing_after: tok })}
          testId={`spacing-below-${instance.id}`}
        />
        {!isProfile && (
          <TokenPicker
            label="Between entries"
            value={spacingTokenToSpacingToken(style.subsection?.spacing_after)}
            onChange={(tok) => updateSubsection({ spacing_after: tok })}
            testId={`spacing-entries-${instance.id}`}
          />
        )}
      </Group>

      {/* ── Page break ───────────────────────────────────────────── */}
      {showPageBreak && (
        <Group title="Page break">
          <Row label="Start on a new page">
            <input
              type="checkbox"
              checked={!!style.layout?.break_before}
              onChange={(e) => updateLayout({ break_before: e.target.checked })}
              className="h-3.5 w-3.5"
              aria-label="Start on a new page"
            />
          </Row>
        </Group>
      )}

      {/* ── Alignment ────────────────────────────────────────────── */}
      {showTextAlign && (
        <Group title="Alignment">
          <Row label="Text align">
            <div className="flex flex-wrap items-center gap-1.5" role="radiogroup" aria-label="Text align">
              {(["left", "center", "right", "justify"] as const).map((tok) => {
                const disabled = isTwoColumn;
                return (
                  <button
                    key={tok}
                    type="button"
                    role="radio"
                    aria-checked={style.subsection?.text_align === tok}
                    disabled={disabled}
                    onClick={() => updateSubsection({ text_align: tok })}
                    className="rounded px-2 py-0.5 text-xs transition-colors disabled:opacity-50"
                    style={{
                      background: style.subsection?.text_align === tok ? ink.ink : "transparent",
                      color: style.subsection?.text_align === tok ? "white" : ink.ink,
                      border: `1px solid ${ruleDefault}`,
                      borderRadius: radius.r1,
                    }}
                    title={disabled ? "Not applicable to two-column entries" : undefined}
                  >
                    {tok.charAt(0).toUpperCase() + tok.slice(1)}
                  </button>
                );
              })}
            </div>
          </Row>
          {isTwoColumn && (
            <p className="text-xs" style={{ color: ink.ink3 }}>
              Two-column entry layouts ignore text alignment.
            </p>
          )}
        </Group>
      )}

      {/* ── Typography ───────────────────────────────────────────── */}
      {fields.length > 0 && (
        <Group title="Typography">
          {fields.map((f) => (
            <TypographyRow
              key={f.key}
              label={f.label}
              sample={f.sample}
              current={style.text?.[f.key] ?? {}}
              isRichText={f.isRichText}
              onChange={(next) => updateText(f.key, next)}
              testId={`typography-${instance.id}-${f.key}`}
            />
          ))}
        </Group>
      )}
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded p-3" style={{ border: `1px solid ${ruleDefault}` }}>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide" style={{ color: ink.ink3 }}>
        {title}
      </h3>
      <div className="space-y-2">{children}</div>
    </section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-32 text-xs" style={{ color: ink.ink3 }}>{label}</span>
      <div>{children}</div>
    </div>
  );
}

/** Map a raw CSS string from the wire (or null) to a section-spacing
 * token for the picker. Anything unrecognised falls back to null so
 * the picker shows the Default pill.
 */
function spacingTokenToSpacingToken(raw: string | null | undefined): SectionSpacingToken | null {
  if (!raw) return null;
  if ((SECTION_SPACING_TOKENS as readonly string[]).includes(raw)) {
    return raw as SectionSpacingToken;
  }
  const px = parseInt(raw);
  if (Number.isNaN(px)) return null;
  if (px <= 6) return "none";
  if (px <= 18) return "tight";
  if (px <= 28) return "comfortable";
  return "loose";
}
