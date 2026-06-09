import type { SkillGroup, SectionStyle } from "../../../lib/sections/types";

interface Props {
  data: SkillGroup[] | undefined;
  style?: SectionStyle;
}

export default function SkillsRenderer({ data = [], style }: Props) {
  const layout = style?.layout === "inline" ? "inline" : "block";
  if (layout === "inline") {
    return (
      <div className="space-y-1">
        {data.map((group) => (
          <div key={group.id}>
            <span className="text-sm font-semibold">{group.category}</span>
            {group.category && group.items.length > 0 && ": "}
            <span className="text-sm">{group.items.join(", ")}</span>
          </div>
        ))}
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {data.map((group) => (
        <div key={group.id}>
          <h3 className="text-sm font-semibold">{group.category}</h3>
          <div className="mt-1 flex flex-wrap gap-1">
            {group.items.map((item, i) => (
              <span key={i} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">{item}</span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
