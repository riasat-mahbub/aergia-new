import { DATE_STYLE_OPTIONS } from "@/shared/cv/date";
import { ink, radius, ruleDefault } from "@/styles/tokens";
import { Group, Row } from "./Controls";
import type { SectionStyleGroupProps } from "./types";

export function PageBreakGroup({ instance, style, updateLayout }: SectionStyleGroupProps) {
  if (instance.type === "profile") return null;
  return (
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
  );
}

export function DatesGroup({ instance, style, updateLayout }: SectionStyleGroupProps) {
  const dateSectionTypes = new Set(["experience", "education", "projects", "research", "certifications"]);
  if (!dateSectionTypes.has(instance.type)) return null;
  return (
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
                  rangeSep: DATE_STYLE_OPTIONS.find((option) => option.value === key)?.rangeSep ?? " – ",
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
          {DATE_STYLE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </Row>
    </Group>
  );
}

export function AlignmentGroup({ instance, style, updateSubsection }: SectionStyleGroupProps) {
  if (instance.type === "profile") return null;
  const isTwoColumn = style.policy?.entry_layout === "two-column";
  return (
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
  );
}
