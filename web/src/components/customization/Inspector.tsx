/**
 * Inspector — top-level replacement for CustomizePanel.
 *
 * Three surfaces, top to bottom:
 *
 *   A. Document strip (always visible) — body font, heading font,
 *      accent color. Per-section override chips inline.
 *   B. Sections list — one card per section, exclusive accordion.
 *      Each card opens to a SectionInspector.
 *   C. Footer — template name + change + reset-to-defaults.
 *
 * The component does NOT mount the section-zone-view (the structural
 * DnD authoring surface). The BuilderPage already owns that as a
 * separate concern; the customize tab is the inspector for already-
 * authored sections, not the place to add or remove them.
 *
 * Writes flow back through three callbacks:
 *   - onCustomizationsChange for the document strip
 *   - onUpdateStyle(id, style) for the per-section inspector
 *   - onTemplateChange / onReset for the footer
 */

import { useEffect, useState } from "react";
import type { SectionInstance, SectionInstanceStyle } from "../../lib/sections/types";
import { SECTION_LABELS } from "../../lib/sections/types";
import { FONT_TOKEN_LABELS, FONT_TOKENS } from "../../styles/tokens";
import type { FontToken } from "../../styles/tokens";
import { ink, rule, accent } from "../../styles/tokens";
import ColorChip from "./controls/ColorChip";
import OverridePill from "./controls/OverridePill";
import ResetFooter from "./controls/ResetFooter";
import SectionInspector from "./SectionInspector";

interface Props {
  templateId: string;
  /** Display name for the template — comes from the manifest. Falls
   * back to a humanized form of the id when the manifest isn't loaded. */
  templateName: string;
  instances: SectionInstance[];
  onUpdateStyle: (id: string, style: SectionInstanceStyle) => void;
  onCustomizationsChange: (customizations: Record<string, unknown>) => void;
  onTemplateChange: () => void;
  onReset: () => void;
  customizations: Record<string, unknown>;
}

export default function Inspector({
  templateId,
  templateName,
  instances,
  onUpdateStyle,
  onCustomizationsChange,
  onTemplateChange,
  onReset,
  customizations,
}: Props) {
  const [openId, setOpenId] = useState<string | null>(instances[0]?.id ?? null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- selection follows the instances list; the dependency array is correct
    if (!openId && instances[0]) setOpenId(instances[0].id);
    if (openId && !instances.some((i) => i.id === openId)) {
      setOpenId(instances[0]?.id ?? null);
    }
  }, [instances, openId]);

  const docBodyFont = (customizations.body_font as FontToken | undefined) ?? null;
  const docHeadingFont = (customizations.heading_font as FontToken | undefined) ?? null;
  const docAccent = (customizations.accent_color as string | undefined) ?? null;

  const updateCustomization = (key: string, value: unknown) => {
    const next: Record<string, unknown> = { ...customizations };
    if (value === null || value === undefined || value === "") {
      delete next[key];
    } else {
      next[key] = value;
    }
    onCustomizationsChange(next);
  };

  const accentOverrides = instances.filter((i) => !!i.style?.subsection?.section_color);
  const bodyFontOverrides = instances.filter((i) => !!i.style?.layout?.font_family);

  const displayedTemplateName = templateName || templateIdShort(templateId);

  return (
    <div data-testid="inspector">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide" style={{ color: ink.ink2 }}>
        Customize
      </h3>

      {/* ── A. Document strip ──────────────────────────────────────── */}
      <section className="mb-4 rounded p-3" style={{ border: `1px solid ${rule}` }}>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide" style={{ color: ink.ink3 }}>
          Document style
        </h4>
        <div className="space-y-2">
          <DocRow label="Body font">
            <select
              value={docBodyFont ?? ""}
              onChange={(e) => updateCustomization("body_font", e.target.value || null)}
              className="rounded border px-2 py-1 text-xs"
              style={{ borderColor: rule }}
              aria-label="Body font"
              data-testid="document-body-font"
            >
              <option value="">Default ({FONT_TOKEN_LABELS["sans-serif"]})</option>
              {FONT_TOKENS.map((tok) => (
                <option key={tok} value={tok}>{FONT_TOKEN_LABELS[tok]}</option>
              ))}
            </select>
            <OverridePill
              sections={bodyFontOverrides.map((i) => i.title)}
              onJump={() => {
                const first = bodyFontOverrides[0];
                if (first) setOpenId(first.id);
              }}
            />
          </DocRow>

          <DocRow label="Heading font">
            <select
              value={docHeadingFont ?? ""}
              onChange={(e) => updateCustomization("heading_font", e.target.value || null)}
              className="rounded border px-2 py-1 text-xs"
              style={{ borderColor: rule }}
              aria-label="Heading font"
              data-testid="document-heading-font"
            >
              <option value="">Default ({FONT_TOKEN_LABELS["sans-serif"]})</option>
              {FONT_TOKENS.map((tok) => (
                <option key={tok} value={tok}>{FONT_TOKEN_LABELS[tok]}</option>
              ))}
            </select>
          </DocRow>

          <DocRow label="Accent color">
            <ColorChip
              value={docAccent}
              onChange={(next) => updateCustomization("accent_color", next)}
              label="Accent color"
              testId="document-accent"
            />
            <OverridePill
              sections={accentOverrides.map((i) => i.title)}
              onJump={() => {
                const first = accentOverrides[0];
                if (first) setOpenId(first.id);
              }}
            />
          </DocRow>
        </div>
      </section>

      {/* ── B. Sections list ──────────────────────────────────────── */}
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide" style={{ color: ink.ink3 }}>
        Sections
      </h4>
      <div className="space-y-2">
        {instances.map((inst) => {
          const open = openId === inst.id;
          return (
            <article
              key={inst.id}
              data-testid={`section-card-${inst.id}`}
              className="rounded"
              style={{
                border: `1px solid ${rule}`,
                background: open ? "var(--paper-1)" : "var(--paper)",
              }}
            >
              <button
                type="button"
                onClick={() => setOpenId(open ? null : inst.id)}
                className="flex w-full items-center justify-between rounded px-3 py-2 text-left"
                aria-expanded={open}
                aria-controls={`section-body-${inst.id}`}
              >
                <div>
                  <p className="text-sm font-medium" style={{ color: ink.ink }}>
                    {inst.title}
                  </p>
                  <p className="text-xs" style={{ color: ink.ink3 }}>
                    {SECTION_LABELS[inst.type] || inst.type}
                  </p>
                </div>
                <span
                  className="text-xs"
                  style={{ color: open ? accent.accent : ink.ink3 }}
                  aria-hidden
                >
                  {open ? "▾" : "▸"}
                </span>
              </button>
              {open && (
                <div
                  id={`section-body-${inst.id}`}
                  className="border-t px-3 py-3"
                  style={{ borderColor: rule }}
                >
                  <SectionInspector
                    instance={inst}
                    documentAccent={docAccent}
                    documentBodyFont={docBodyFont}
                    onChange={(style) => onUpdateStyle(inst.id, style)}
                  />
                </div>
              )}
            </article>
          );
        })}
      </div>

      {/* ── C. Footer ─────────────────────────────────────────────── */}
      <ResetFooter
        templateName={displayedTemplateName}
        onChangeTemplate={onTemplateChange}
        onReset={onReset}
        canReset={Object.keys(customizations).length > 0 || instances.some((i) => i.style)}
      />
    </div>
  );
}

function DocRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-28 text-xs" style={{ color: ink.ink3 }}>{label}</span>
      <div className="flex flex-wrap items-center gap-1">{children}</div>
    </div>
  );
}

function templateIdShort(id: string): string {
  if (!id) return "Template";
  const parts = id.split("-");
  return parts.length > 1 ? parts.slice(1).join(" ").replace(/^./, (c) => c.toUpperCase()) : id;
}
