import type { SectionInstance } from "../../lib/sections/types";
import { renderSectionPreview } from "./SectionRegistry";

interface Props {
  instance: SectionInstance;
}

// The React inline preview intentionally does NOT honor instance.style.field_styles.
// Field-level typography is rendered exclusively by the backend pipeline (iframe
// preview at /render/html + PDF export), which injects per-panel CSS via
// `f-{key}` hooks. Touching the React renderers to add field styles would
// duplicate the styling surface in two places; the iframe preview is the
// source of truth, so users refine field typography there.
export default function SectionPreviewPanel({ instance }: Props) {
  const wrapperStyle: React.CSSProperties = {};
  const headingStyle: React.CSSProperties = {};

  if (instance.style?.font) wrapperStyle.fontFamily = instance.style.font;
  if (instance.style?.color) {
    wrapperStyle.color = instance.style.color;
    headingStyle.color = instance.style.color;
  }
  if (instance.style?.weight) headingStyle.fontWeight = instance.style.weight;
  if (instance.style?.text_align) wrapperStyle.textAlign = instance.style.text_align;

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
