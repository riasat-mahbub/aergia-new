import type { SkillGroup } from "../../../lib/sections/types";

interface Props {
  data: SkillGroup[] | undefined;
}

export default function SkillsRenderer({ data = [] }: Props) {
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
