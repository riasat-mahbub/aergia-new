/**
 * SectionInspector — per-section card body.
 *
 * Composes the controls primitives into section-local visual-effect groups:
 *
 *   1. Heading        — show heading toggle, divider toggle, color
 *   2. Spacing        — token picker for space above / below / entries
 *   3. Page break     — start-on-new-page toggle (entry sections only)
 *   4. Alignment      — text align radio chips (disabled for two-column)
 *   5. Typography     — one TypographyRow per actual field
 *
 * Groups are collapsed by default so one section never fills the panel.
 * Controls that don't apply to a given section type are hidden. Rich-text
 * fields skip typography with a redirect to the content editor.
 *
 * Every value is stored on this section. The inherited template value is
 * shown as the empty option; there is no editable global style surface.
 */

import { useMemo, useState } from "react";
import type {
  LayoutHints,
  SectionInstance,
  SectionPolicy,
  SubsectionStyle,
  TextStyle,
  TypographyRole,
} from "@/shared/cv/schema";
import { fieldsForInstance } from "../../domain/customization/fieldsForInstance";
import { DATE_STYLE_OPTIONS } from "@/shared/cv/date";
import { effectiveStyle } from "../../domain/customization/cascade";
import type { SectionInstanceStyle } from "@/shared/cv/schema";
import {
  SECTION_SPACING_TOKENS,
  FONT_SIZE_LABELS,
  FONT_SIZE_TOKENS,
  FONT_TOKEN_LABELS,
  FONT_TOKENS,
  LINE_HEIGHT_LABELS,
  LINE_HEIGHT_TOKENS,
  ink,
  radius,
  ruleDefault,
} from "@/styles/tokens";
import type { SectionSpacingToken } from "@/styles/tokens";
import ColorChip from "./controls/ColorChip";
import TokenPicker from "./controls/TokenPicker";
import TypographyRow from "./controls/TypographyRow";

interface Props {
  instance: SectionInstance;
  inheritedBodyFont: string | null;
  inheritedHeadingFont: string | null;
  inheritedAccent: string | null;
  onChange: (next: SectionInstanceStyle) => void;
}

export default function SectionInspector({
  instance,
  inheritedBodyFont,
  inheritedHeadingFont,
  inheritedAccent,
  onChange,
}: Props) {
  const style = useMemo(() => effectiveStyle(instance.type, instance.style), [instance.type, instance.style]);
  const fields = useMemo(() => fieldsForInstance(instance), [instance]);
  const rawStyle = instance.style ?? {};

  const isProfile = instance.type === "profile";
  const isDateSection = instance.type === "experience"
    || instance.type === "education"
    || instance.type === "projects"
    || instance.type === "research"
    || instance.type === "certifications";
  const isTwoColumn = style.policy?.entry_layout === "two-column";
  const showTextAlign = !isProfile;
  const showPageBreak = !isProfile;
  const showDates = isDateSection;
  const updateSubsection = (partial: Partial<SubsectionStyle>) => {
    onChange(updateAxis(rawStyle, "subsection", partial));
  };

  const updateLayout = (partial: Partial<LayoutHints>) => {
    onChange(updateAxis(rawStyle, "layout", partial));
  };

  const updatePolicy = (partial: Partial<SectionPolicy>) => {
    onChange(updateAxis(rawStyle, "policy", partial));
  };

  const updateText = (key: string, value: TextStyle | undefined) => {
    const next = { ...(rawStyle.text ?? {}) };
    if (value === undefined || Object.keys(value).length === 0) {
      delete next[key];
    } else {
      next[key] = value;
    }
    onChange(cleanStyle({ ...rawStyle, text: next }));
  };

  const updateTypography = (role: "heading" | "body", partial: Partial<TypographyRole>) => {
    const typography: { heading?: TypographyRole | null; body?: TypographyRole | null } = {
      ...(rawStyle.typography ?? {}),
    };
    const current: Record<string, unknown> = { ...(typography[role] ?? {}) };
    for (const [key, value] of Object.entries(partial)) {
      if (value === null || value === undefined || value === "") delete current[key];
      else current[key] = value;
    }
    if (Object.keys(current).length === 0) delete typography[role];
    else typography[role] = current as TypographyRole;
    onChange(cleanStyle({ ...rawStyle, typography }));
  };

  const sectionAccent = style.subsection?.accent_color ?? inheritedAccent;
  const headingColor = style.typography?.heading?.color ?? style.subsection?.section_color ?? null;
  const bodyColor = style.typography?.body?.color ?? style.subsection?.section_color ?? null;
  const rawBodyFont = rawStyle.typography?.body?.font_family
    ?? fontTokenFromLegacyValue(rawStyle.layout?.font_family)
    ?? "";
  const rawHeadingFont = rawStyle.typography?.heading?.font_family ?? "";
  const sectionColorOverridden = !!instance.style?.subsection?.section_color;

  return (
    <div className="space-y-3">
      {/* ── Heading ──────────────────────────────────────────────── */}
      <Group title="Heading" defaultOpen>
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
        <Row label="Heading color">
          <ColorChip
            value={headingColor}
            onChange={(next) => updateTypography("heading", { color: next })}
            label="Heading color"
            showRevert={sectionColorOverridden && !!inheritedAccent}
            onRevert={() => updateSubsection({ section_color: null })}
          />
          {sectionColorOverridden && inheritedAccent && (
            <span className="ml-2 text-xs" style={{ color: ink.ink3 }}>
              Overrides inherited color
            </span>
          )}
        </Row>
        <Row label="Section accent">
          <ColorChip
            value={sectionAccent}
            onChange={(next) => updateSubsection({ accent_color: next })}
            label="Section accent"
            showRevert={!!instance.style?.subsection?.accent_color && !!inheritedAccent}
            onRevert={() => updateSubsection({ accent_color: null })}
          />
        </Row>
        <Row label="Heading font">
          <FontSelect
            value={rawHeadingFont}
            inherited={inheritedHeadingFont}
            onChange={(next) => updateTypography("heading", { font_family: next as TypographyRole["font_family"] || null })}
            ariaLabel="Heading font"
          />
        </Row>
        <Row label="Heading size">
          <select
            value={style.typography?.heading?.font_size ?? ""}
            onChange={(e) => updateTypography("heading", { font_size: e.target.value as TypographyRole["font_size"] || null })}
            className="rounded border px-2 py-1 text-xs"
            style={{ borderColor: ruleDefault }}
            aria-label="Heading size"
          >
            <option value="">Template default</option>
            {FONT_SIZE_TOKENS.map((tok) => <option key={tok} value={tok}>{FONT_SIZE_LABELS[tok]}</option>)}
          </select>
        </Row>
      </Group>

      <Group title="Appearance">
        <Row label="Section background">
          <ColorChip
            value={style.subsection?.background_color ?? null}
            onChange={(next) => updateSubsection({ background_color: next })}
            label="Section background"
            showRevert={!!instance.style?.subsection?.background_color}
            onRevert={() => updateSubsection({ background_color: null })}
          />
        </Row>
      </Group>

      <Group title="Body text">
        <Row label="Body font">
          <FontSelect
            value={rawBodyFont}
            inherited={inheritedBodyFont}
            onChange={(next) => {
              const nextStyle = updateAxis(rawStyle, "layout", { font_family: null });
              const typography = { ...(nextStyle.typography ?? {}) };
              const body = { ...(typography.body ?? {}) };
              if (next) body.font_family = next as never;
              else delete body.font_family;
              typography.body = body;
              onChange(cleanStyle({ ...nextStyle, typography }));
            }}
            ariaLabel="Body font"
          />
        </Row>
        <Row label="Body size">
          <select
            value={style.typography?.body?.font_size ?? ""}
            onChange={(e) => updateTypography("body", { font_size: e.target.value as TypographyRole["font_size"] || null })}
            className="rounded border px-2 py-1 text-xs"
            style={{ borderColor: ruleDefault }}
            aria-label="Body size"
          >
            <option value="">Template default</option>
            {FONT_SIZE_TOKENS.map((tok) => <option key={tok} value={tok}>{FONT_SIZE_LABELS[tok]}</option>)}
          </select>
        </Row>
        <Row label="Line height">
          <select
            value={style.typography?.body?.line_height ?? ""}
            onChange={(e) => updateTypography("body", { line_height: e.target.value as TypographyRole["line_height"] || null })}
            className="rounded border px-2 py-1 text-xs"
            style={{ borderColor: ruleDefault }}
            aria-label="Body line height"
          >
            <option value="">Template default</option>
            {LINE_HEIGHT_TOKENS.map((tok) => <option key={tok} value={tok}>{LINE_HEIGHT_LABELS[tok]}</option>)}
          </select>
        </Row>
        <Row label="Body color">
          <ColorChip value={bodyColor} onChange={(next) => updateTypography("body", { color: next })} label="Body color" />
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
            value={spacingTokenToSpacingToken(style.subsection?.entry_gap)}
            onChange={(tok) => updateSubsection({ entry_gap: tok })}
            testId={`spacing-entries-${instance.id}`}
          />
        )}
        <TokenPicker
          label="Between fields"
          value={spacingTokenToSpacingToken(style.subsection?.field_gap)}
          onChange={(tok) => updateSubsection({ field_gap: tok })}
          testId={`spacing-fields-${instance.id}`}
        />
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
      {/* ── Dates ───────────────────────────────────────────────── */}
      {showDates && (
        <Group title="Dates">
          <Row label="Date format">
            <select
              value={style.layout?.date_style?.key ?? ""}
              onChange={(e) => {
                const key = e.target.value;
                if (!key) {
                  updateLayout({ date_style: null });
                } else {
                  updateLayout({
                    date_style: {
                      key,
                      rangeSep: DATE_STYLE_OPTIONS.find(o => o.value === key)?.rangeSep ?? " – ",
                    },
                  });
                }
              }}
              className="rounded border px-2 py-1 text-xs"
              style={{ borderColor: ruleDefault }}
              aria-label="Date format"
              data-testid={`date-format-${instance.id}`}
            >
              <option value="">Default (Month YYYY)</option>
              {DATE_STYLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
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
        <Group title="Advanced field overrides">
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
      <button
        type="button"
        onClick={() => onChange({})}
        className="w-full rounded border px-3 py-1.5 text-xs"
        style={{ borderColor: ruleDefault, color: ink.ink3 }}
      >
        Reset this section
      </button>
    </div>
  );
}

function Group({ title, children, defaultOpen = false }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="rounded" style={{ border: `1px solid ${ruleDefault}` }}>
      <button
        type="button"
        className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide"
        style={{ color: ink.ink3 }}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {title}<span aria-hidden>{open ? "▾" : "▸"}</span>
      </button>
      {open && <div className="space-y-2 border-t p-3" style={{ borderColor: ruleDefault }}>{children}</div>}
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

function FontSelect({ value, inherited, onChange, ariaLabel }: { value: string; inherited: string | null; onChange: (value: string) => void; ariaLabel: string }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded border px-2 py-1 text-xs"
      style={{ borderColor: ruleDefault }}
      aria-label={ariaLabel}
    >
      <option value="">Inherited ({inherited ? FONT_TOKEN_LABELS[inherited as keyof typeof FONT_TOKEN_LABELS] ?? inherited : "default"})</option>
      {FONT_TOKENS.map((tok) => <option key={tok} value={tok}>{FONT_TOKEN_LABELS[tok]}</option>)}
    </select>
  );
}

function cleanStyle(style: SectionInstanceStyle): SectionInstanceStyle {
  const next = { ...style } as Record<string, unknown>;
  for (const key of ["subsection", "layout", "typography", "policy", "text"]) {
    const value = next[key];
    if (value && typeof value === "object" && Object.keys(value as object).length === 0) delete next[key];
  }
  return next as SectionInstanceStyle;
}

function fontTokenFromLegacyValue(value: string | null | undefined): string | null {
  if (!value) return null;
  if ((FONT_TOKENS as readonly string[]).includes(value)) return value;
  if (/mono|monospace/i.test(value)) return "mono";
  if (/Georgia|Crimson|serif/i.test(value)) return "serif";
  if (/Inter|system-ui|sans-serif/i.test(value)) return "sans-serif";
  return null;
}

function updateAxis<K extends "subsection" | "layout" | "policy">(
  style: SectionInstanceStyle,
  axis: K,
  partial: Partial<NonNullable<SectionInstanceStyle[K]>>,
): SectionInstanceStyle {
  const current = { ...((style[axis] ?? {}) as object), ...partial } as Record<string, unknown>;
  for (const [key, value] of Object.entries(current)) {
    if (value === null || value === undefined || value === "") delete current[key];
  }
  return cleanStyle({ ...style, [axis]: current });
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
  if (px <= 34) return "loose";
  return "spacious";
}
