import type { TypographyRole } from "@/shared/cv/schema";
import { FONT_SIZE_LABELS, FONT_SIZE_TOKENS, ink, ruleDefault } from "@/styles/tokens";
import ColorChip from "../controls/ColorChip";
import { FontSelect, Group, Row } from "./Controls";
import type { SectionStyleGroupProps } from "./types";

export default function HeadingGroup({
  instance,
  style,
  rawStyle,
  inheritedHeadingFont,
  inheritedAccent,
  updateSubsection,
  updatePolicy,
  updateTypography,
}: SectionStyleGroupProps) {
  const isProfile = instance.type === "profile";
  const sectionAccent = style.subsection?.accent_color ?? inheritedAccent;
  const headingColor = style.typography?.heading?.color ?? style.subsection?.section_color ?? null;
  const rawHeadingFont = rawStyle.typography?.heading?.font_family ?? "";
  const sectionColorOverridden = !!rawStyle.subsection?.section_color;

  return (
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
          showRevert={!!rawStyle.subsection?.accent_color && !!inheritedAccent}
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
  );
}
