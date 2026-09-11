import type { TypographyRole } from "@/shared/cv/schema";
import { FONT_SIZE_LABELS, FONT_SIZE_TOKENS, LINE_HEIGHT_LABELS, LINE_HEIGHT_TOKENS, ruleDefault } from "@/styles/tokens";
import ColorChip from "../controls/ColorChip";
import { FontSelect, Group, Row } from "./Controls";
import { cleanStyle, fontTokenFromLegacyValue, updateAxis } from "./stylePatches";
import type { SectionStyleGroupProps } from "./types";

export default function BodyTextGroup({
  style,
  rawStyle,
  inheritedBodyFont,
  updateTypography,
  onChange,
}: SectionStyleGroupProps) {
  const bodyColor = style.typography?.body?.color ?? style.subsection?.section_color ?? null;
  const rawBodyFont = rawStyle.typography?.body?.font_family
    ?? fontTokenFromLegacyValue(rawStyle.layout?.font_family)
    ?? "";

  return (
    <Group title="Body text">
      <Row label="Body font">
        <FontSelect
          value={rawBodyFont}
          inherited={inheritedBodyFont}
          onChange={(next) => {
            const nextStyle = updateAxis(rawStyle, "layout", { font_family: null });
            const typography = { ...(nextStyle.typography ?? {}) };
            const body = { ...(typography.body ?? {}) };
            if (next) body.font_family = next as TypographyRole["font_family"];
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
  );
}
