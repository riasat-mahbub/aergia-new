import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from "react";
import * as templatesApi from "@/features/templates";
import { updateCV } from "@/features/cvs";
import type { UserTemplate } from "@/features/templates";
import type { SectionInstance } from "@/shared/cv/schema";
import type { LayoutConfig } from "@/shared/cv/placement";
import { getFirstZoneId } from "@/shared/cv/placement";

interface UseTemplateManifestOptions {
  id: string;
  templateId: string | undefined;
  isLoaded: boolean;
  instances: SectionInstance[];
  customizations: Record<string, unknown>;
  setInstances: Dispatch<SetStateAction<SectionInstance[]>>;
  setCustomizations: Dispatch<SetStateAction<Record<string, unknown>>>;
  setIsSaving: (saving: boolean) => void;
  loadCV: (id: string) => Promise<void>;
}

export function useTemplateManifest({
  id,
  templateId,
  isLoaded,
  instances,
  customizations,
  setInstances,
  setCustomizations,
  setIsSaving,
  loadCV,
}: UseTemplateManifestOptions) {
  const [templateManifest, setTemplateManifest] = useState<UserTemplate | null>(null);

  useEffect(() => {
    if (!templateId || !isLoaded) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- clear stale manifest before loading the next template
    setTemplateManifest(null);
    let cancelled = false;
    (async () => {
      try {
        const template = await templatesApi.fetchTemplate(templateId);
        if (!cancelled) setTemplateManifest(template ?? null);
      } catch {
        if (!cancelled) setTemplateManifest(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isLoaded, templateId]);

  const handleTemplateChange = useCallback(
    async (newTemplateId: string) => {
      if (!id) return;
      if (
        !window.confirm(
          "Switching templates installs the new template's zones and reassigns every section to the first zone. Per-section content (text, entries, order) is preserved. Continue?",
        )
      ) {
        return;
      }

      try {
        setIsSaving(true);
        const cleanInstances = instances.map((instance) => ({ ...instance, style: undefined }));
        setInstances(cleanInstances);

        let nextCustomizations: Record<string, unknown>;
        try {
          const template = await templatesApi.fetchTemplate(newTemplateId);
          const zones = template.manifest?.zones;
          const placement = template.manifest?.placement;
          if (Array.isArray(zones) && zones.length > 0 && placement) {
            const newLayout: LayoutConfig = { zones, placement: {} };
            const firstZoneId = getFirstZoneId(newLayout);
            for (const instance of cleanInstances) {
              if (firstZoneId) newLayout.placement[instance.id] = firstZoneId;
            }
            nextCustomizations = { ...customizations, layout: newLayout };
          } else {
            nextCustomizations = {};
          }
        } catch {
          nextCustomizations = {};
        }
        setCustomizations(nextCustomizations);

        await updateCV(id, {
          template_id: newTemplateId,
          sections: cleanInstances,
          customizations: nextCustomizations,
        });
        await loadCV(id);
      } finally {
        setIsSaving(false);
      }
    },
    [customizations, id, instances, loadCV, setCustomizations, setInstances, setIsSaving],
  );

  return { templateManifest, handleTemplateChange };
}
