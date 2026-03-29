import type { SectionInstance } from "../../lib/sections/types";
import { renderSectionPreview } from "./SectionRegistry";

interface Props {
  instance: SectionInstance;
}

export default function SectionPreviewPanel({ instance }: Props) {
  if (!instance.enabled) return null;

  const wrapperStyle: React.CSSProperties = {};
  const headingStyle: React.CSSProperties = {};

  if (instance.style?.font) wrapperStyle.fontFamily = instance.style.font;
  if (instance.style?.color) {
    wrapperStyle.color = instance.style.color;
    headingStyle.color = instance.style.color;
  }
  if (instance.style?.weight) headingStyle.fontWeight = instance.style.weight;

  return (
    <div className={`mb-6 section-${instance.type}`} style={wrapperStyle}>
      <h2 className="mb-2 text-base font-bold uppercase tracking-wide text-gray-800" style={headingStyle}>
        {instance.title}
      </h2>
      {renderSectionPreview(instance.type, instance.data) || (
        <p className="text-sm text-gray-400 italic">No data</p>
      )}
    </div>
  );
}
