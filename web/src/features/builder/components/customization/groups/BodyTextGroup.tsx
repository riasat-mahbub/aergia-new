import type { TypographyRole } from "@/shared/cv/schema";
import { FONT_SIZE_CSS, FONT_SIZE_LABELS, FONT_SIZE_TOKENS, LINE_HEIGHT_LABELS, LINE_HEIGHT_TOKENS, ruleDefault, ink } from "@/styles/tokens";
import type { FontSizeToken, LineHeightToken } from "@/styles/tokens";
import ColorChip from "../controls/ColorChip";
import { FontSelect, Group, Row } from "./Controls";
import { cleanStyle } from "./stylePatches";
import type { SectionStyleGroupProps } from "./types";

export default function BodyTextGroup({
  style,
  rawStyle,
  inheritedBodyFont,
  inheritedBodySize,
  inheritedBodyLineHeight,
  instance,
  updateTypography,
  onChange,
}: SectionStyleGroupProps) {
  const bodyColor = style.typography?.body?.color ?? style.subsection?.section_color ?? null;
  const rawBodyFont = rawStyle.typography?.body?.font_family ?? "";
  const bodySizeValue = style.typography?.body?.font_size ?? "";
  const lineHeightValue = style.typography?.body?.line_height ?? "";

  return (
    <Group title="Body text">
      <Row label="Body font">
        <FontSelect
          value={rawBodyFont}
          inherited={inheritedBodyFont}
          onChange={(next) => {
            const typography = { ...(rawStyle.typography ?? {}) };
            const body = { ...(typography.body ?? {}) };
            if (next) body.font_family = next as TypographyRole["font_family"];
            else delete body.font_family;
            typography.body = body;
            onChange(cleanStyle({ ...rawStyle, typography }));
          }}
          ariaLabel="Body font"
        />
      </Row>
      <Row label="Body size">
        <div className="space-y-1">
          <select
            value={bodySizeValue}
            onChange={(e) => updateTypography("body", { font_size: e.target.value as TypographyRole["font_size"] || null })}
            className="rounded border px-2 py-1 text-xs"
            style={{ borderColor: ruleDefault }}
            aria-label="Body size"
          >
            <option value="">{inheritedBodySize ? `Template default (${fontSizePt(inheritedBodySize)})` : "Template default"}</option>
            {FONT_SIZE_TOKENS.map((tok) => <option key={tok} value={tok}>{FONT_SIZE_LABELS[tok]}</option>)}
          </select>
          {instance.type === "profile" && bodySizeValue === "" && (
            <p className="text-[11px] leading-4" style={{ color: ink.ink3 }}>
              The candidate name keeps its separate size.
            </p>
          )}
        </div>
      </Row>
      <Row label="Line height">
        <select
          value={lineHeightValue}
          onChange={(e) => updateTypography("body", { line_height: e.target.value as TypographyRole["line_height"] || null })}
          className="rounded border px-2 py-1 text-xs"
          style={{ borderColor: ruleDefault }}
          aria-label="Body line height"
        >
          <option value="">{inheritedBodyLineHeight ? `Template default (${lineHeightLabel(inheritedBodyLineHeight)})` : "Template default"}</option>
          {LINE_HEIGHT_TOKENS.map((tok) => <option key={tok} value={tok}>{LINE_HEIGHT_LABELS[tok]}</option>)}
        </select>
      </Row>
      <Row label="Body color">
        <ColorChip value={bodyColor} onChange={(next) => updateTypography("body", { color: next })} label="Body color" />
      </Row>
    </Group>
  );
}

function fontSizePt(token: FontSizeToken): string {
  const cssSize = FONT_SIZE_CSS[token];
  if (!cssSize.endsWith("rem")) return FONT_SIZE_LABELS[token];
  const points = Number.parseFloat(cssSize) * 12;
  return `${Number.isInteger(points) ? points : points.toFixed(1)} pt`;
}

function lineHeightLabel(token: LineHeightToken): string {
  const ratio = { tight: "1.2", normal: "1.4", relaxed: "1.7" }[token];
  return `${LINE_HEIGHT_LABELS[token]} · ${ratio}`;
}
