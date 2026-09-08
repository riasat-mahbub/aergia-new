/**
 * Inspector — the section-local Customize surface.
 *
 * The panel has no editable document-style controls. Each section owns its
 * own heading, typography, spacing, layout, and field overrides. Empty
 * controls inherit the template (or a legacy saved document value), so an
 * existing CV remains readable without reintroducing a global editor.
 */

import { useEffect, useState } from "react";
import type { SectionInstance, SectionInstanceStyle } from "@/shared/cv/schema";
import { SECTION_LABELS } from "@/shared/cv/sectionCatalog";
import { ink, ruleDefault, accent } from "@/styles/tokens";
import { sectionStyleHasValues } from "../../domain/sectionStyle";
import ResetFooter from "./controls/ResetFooter";
import SectionInspector from "./SectionInspector";

interface Props {
  templateId: string;
  /** Display name for the template — comes from the manifest. */
  templateName: string;
  templateBodyFont?: string | null;
  templateHeadingFont?: string | null;
  templateAccent?: string | null;
  instances: SectionInstance[];
  onUpdateStyle: (id: string, style: SectionInstanceStyle) => void;
  onTemplateChange: () => void | Promise<void>;
  onReset: () => void;
  /** Legacy document values are read only and used as the inherited value. */
  customizations: Record<string, unknown>;
}

export default function Inspector({
  templateId,
  templateName,
  templateBodyFont,
  templateHeadingFont,
  templateAccent,
  instances,
  onUpdateStyle,
  onTemplateChange,
  onReset,
  customizations,
}: Props) {
  // Start with no card open. The previous implementation selected the first
  // section on every load, which made a long inspector fill the whole panel.
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    // Keep a selected card only while it still exists. Do not select a
    // replacement automatically: all sections may be closed by the user.
    if (openId && !instances.some((instance) => instance.id === openId)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- selection follows removed instances
      setOpenId(null);
    }
  }, [instances, openId]);

  const inheritedBodyFont = stringValue(customizations.body_font) ?? templateBodyFont ?? null;
  const inheritedHeadingFont = stringValue(customizations.heading_font) ?? templateHeadingFont ?? null;
  const inheritedAccent = stringValue(customizations.accent_color) ?? templateAccent ?? null;
  const displayedTemplateName = templateName || templateIdShort(templateId);
  const hasLegacyStyle = [
    "body_font",
    "heading_font",
    "accent_color",
    "default_text_align",
    "spacing",
  ].some((key) => customizations[key] !== undefined && customizations[key] !== null);
  const canReset = hasLegacyStyle || instances.some((instance) => instance.style && sectionStyleHasValues(instance.style));

  return (
    <div data-testid="inspector">
      <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide" style={{ color: ink.ink2 }}>
        Customize
      </h3>
      <p className="mb-4 text-xs" style={{ color: ink.ink3 }}>
        Choose a section to edit. Empty values use the template defaults.
      </p>

      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide" style={{ color: ink.ink3 }}>
        Sections
      </h4>
      <div className="space-y-2">
        {instances.map((inst) => {
          const open = openId === inst.id;
          const hasOverrides = Boolean(inst.style && sectionStyleHasValues(inst.style));
          return (
            <article
              key={inst.id}
              data-testid={`section-card-${inst.id}`}
              className="rounded"
              style={{
                border: `1px solid ${ruleDefault}`,
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
                    {hasOverrides ? " · Customized" : ""}
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
                  style={{ borderColor: ruleDefault }}
                >
                  <SectionInspector
                    instance={inst}
                    inheritedBodyFont={inheritedBodyFont}
                    inheritedHeadingFont={inheritedHeadingFont}
                    inheritedAccent={inheritedAccent}
                    onChange={(style) => onUpdateStyle(inst.id, style)}
                  />
                </div>
              )}
            </article>
          );
        })}
      </div>

      <ResetFooter
        templateName={displayedTemplateName}
        onChangeTemplate={onTemplateChange}
        onReset={onReset}
        canReset={canReset}
      />
    </div>
  );
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function templateIdShort(id: string): string {
  if (!id) return "Template";
  const parts = id.split("-");
  return parts.length > 1 ? parts.slice(1).join(" ").replace(/^./, (c) => c.toUpperCase()) : id;
}
