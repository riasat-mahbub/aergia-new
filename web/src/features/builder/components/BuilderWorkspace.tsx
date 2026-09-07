import { motion } from "motion/react";
import type { CVDetail } from "@/features/cvs";
import type { UserTemplate } from "@/features/templates";
import type { SectionInstance, SectionInstanceStyle } from "@/shared/cv/schema";
import ContentSectionList from "./ContentSectionList";
import Inspector from "./customization/Inspector";
import UserTemplateRenderer from "./preview/UserTemplateRenderer";

interface BuilderWorkspaceProps {
  cv: CVDetail;
  cvId: string;
  instances: SectionInstance[];
  customizations: Record<string, unknown>;
  templateManifest: UserTemplate | null;
  activeTab: "content" | "customize";
  onTabChange: (tab: "content" | "customize") => void;
  onToggle: (sectionId: string) => void;
  onUpdateData: (sectionId: string, data: unknown) => void;
  onAddSection: (type: string) => void;
  onRemoveInstance: (sectionId: string) => void;
  onRenameInstance: (sectionId: string, title: string) => void;
  onReorderInstances: (instances: SectionInstance[]) => void;
  onUpdateStyle: (sectionId: string, style: SectionInstanceStyle) => void;
  onCustomizationsChange: (customizations: Record<string, unknown>) => void;
  onTemplateChange: () => void | Promise<void>;
  onReset: () => void;
}

export default function BuilderWorkspace({
  cv,
  cvId,
  instances,
  customizations,
  templateManifest,
  activeTab,
  onTabChange,
  onToggle,
  onUpdateData,
  onAddSection,
  onRemoveInstance,
  onRenameInstance,
  onReorderInstances,
  onUpdateStyle,
  onCustomizationsChange,
  onTemplateChange,
  onReset,
}: BuilderWorkspaceProps) {
  return (
    <div className="flex flex-1 overflow-hidden">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        className="flex w-1/2 flex-col overflow-hidden border-r bg-app-surface"
      >
        <div className="flex border-b bg-app-canvas">
          <button
            onClick={() => onTabChange("content")}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "content"
                ? "border-b-2 border-app-primary bg-app-surface text-app-primary"
                : "text-app-ink-3 hover:text-app-ink-2"
            }`}
          >
            Content
          </button>
          <button
            onClick={() => onTabChange("customize")}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "customize"
                ? "border-b-2 border-app-primary bg-app-surface text-app-primary"
                : "text-app-ink-3 hover:text-app-ink-2"
            }`}
          >
            Customize
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === "customize" && (
            <Inspector
              templateId={cv.template_id}
              templateName={templateManifest?.name ?? ""}
              instances={instances}
              onUpdateStyle={onUpdateStyle}
              onCustomizationsChange={onCustomizationsChange}
              onTemplateChange={onTemplateChange}
              onReset={onReset}
              customizations={customizations}
            />
          )}
          {activeTab === "content" && (
            <ContentSectionList
              instances={instances}
              cvId={cvId}
              onToggle={onToggle}
              onUpdateData={onUpdateData}
              onAddSection={onAddSection}
              onRemoveInstance={onRemoveInstance}
              onRenameInstance={onRenameInstance}
              onReorderInstances={onReorderInstances}
            />
          )}
        </div>
      </motion.div>
      <motion.div
        initial={{ x: 20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="w-1/2 overflow-y-auto bg-app-surface-muted p-6"
      >
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-app-ink-3">Preview</h2>
        <div className="w-full min-w-0">
          <UserTemplateRenderer
            instances={instances}
            customizations={customizations}
            manifest={templateManifest?.manifest ?? undefined}
          />
        </div>
      </motion.div>
    </div>
  );
}
