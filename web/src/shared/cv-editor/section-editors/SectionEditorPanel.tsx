import type { SectionInstance } from "@/shared/cv/schema";
import { renderSectionEditor } from "./SectionRegistry";
import type { SectionEditorActions, SectionEditorMode } from "./types";

interface Props {
  instance: SectionInstance;
  onChange: (id: string, data: unknown) => void;
  mode?: SectionEditorMode;
  actions?: SectionEditorActions;
}

export default function SectionEditorPanel({
  instance,
  onChange,
  mode = "section",
  actions,
}: Props) {
  const handleSectionChange = (newData: unknown) => {
    onChange(instance.id, newData);
  };

  return (
    <div
      className={`rounded-lg border ${instance.enabled ? "border-app-rule" : "border-dashed border-app-rule-strong"} bg-app-surface p-4`}
    >
      {instance.enabled &&
        renderSectionEditor(
          instance.type,
          instance.data,
          handleSectionChange,
          mode,
          actions,
        )}
    </div>
  );
}
