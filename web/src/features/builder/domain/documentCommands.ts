import type { SectionInstance, SectionInstanceStyle } from "@/shared/cv/schema";
import { createDefaultInstance } from "@/shared/cv/sectionCatalog";
import { getFirstZoneId, type LayoutConfig } from "@/shared/cv/placement";
import { sectionStyleHasValues } from "./sectionStyle";

export function toggleInstance(instances: SectionInstance[], sectionId: string): SectionInstance[] {
  return instances.map((instance) =>
    instance.id === sectionId ? { ...instance, enabled: !instance.enabled } : instance,
  );
}

export function updateInstanceData(
  instances: SectionInstance[],
  sectionId: string,
  data: unknown,
): SectionInstance[] {
  if (Array.isArray(data) && data.length === 0) {
    return instances.filter((instance) => instance.id !== sectionId);
  }
  return instances.map((instance) =>
    instance.id === sectionId ? { ...instance, data: data as SectionInstance["data"] } : instance,
  );
}

export function removeInstance(instances: SectionInstance[], sectionId: string): SectionInstance[] {
  return instances.filter((instance) => instance.id !== sectionId);
}

export function renameInstance(
  instances: SectionInstance[],
  sectionId: string,
  title: string,
): SectionInstance[] {
  return instances.map((instance) => (instance.id === sectionId ? { ...instance, title } : instance));
}

export function updateInstanceStyle(
  instances: SectionInstance[],
  sectionId: string,
  style: SectionInstanceStyle,
): SectionInstance[] {
  const nextStyle = sectionStyleHasValues(style) ? style : undefined;
  return instances.map((instance) =>
    instance.id === sectionId ? { ...instance, style: nextStyle } : instance,
  );
}

export function resetDocument(instances: SectionInstance[]): SectionInstance[] {
  return instances.map((instance) => ({ ...instance, style: undefined }));
}

export interface AddedSectionDocument {
  instance: SectionInstance;
  instances: SectionInstance[];
  customizations: Record<string, unknown>;
}

export function addSection(
  instances: SectionInstance[],
  customizations: Record<string, unknown>,
  type: string,
  zoneId?: string,
): AddedSectionDocument {
  const instance = createDefaultInstance(type);
  const existingLayout = customizations.layout as LayoutConfig | undefined;
  const hasValidLayout = Boolean(existingLayout?.zones?.length);
  const baseLayout: LayoutConfig = hasValidLayout
    ? existingLayout!
    : { zones: [], placement: {} };
  const targetZoneId = zoneId ?? getFirstZoneId(baseLayout);

  if (!targetZoneId) {
    return { instance, instances: [...instances, instance], customizations };
  }

  return {
    instance,
    instances: [...instances, instance],
    customizations: {
      ...customizations,
      layout: {
        ...baseLayout,
        placement: { ...baseLayout.placement, [instance.id]: targetZoneId },
      },
    },
  };
}
