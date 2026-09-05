import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import type { SectionInstance } from "@/lib/cv/schema";
import type { LayoutConfig } from "@/lib/cv/placement";
import { migratePlacement } from "@/lib/cv/placement";
import { useBuilderDocumentStore } from "../_stores/builderDocumentStore";

interface UseBuilderDocumentLoaderOptions {
  id: string;
  loadCV: (id: string) => Promise<void>;
}

export interface BuilderDocumentDraft {
  instances: SectionInstance[];
  customizations: Record<string, unknown>;
  setInstances: Dispatch<SetStateAction<SectionInstance[]>>;
  setCustomizations: Dispatch<SetStateAction<Record<string, unknown>>>;
  isLoaded: boolean;
  showLoading: boolean;
}

/** Loads one route document and normalizes legacy placement before editing starts. */
export function useBuilderDocumentLoader({ id, loadCV }: UseBuilderDocumentLoaderOptions): BuilderDocumentDraft {
  const [showLoading, setShowLoading] = useState(true);
  const [instances, setInstances] = useState<SectionInstance[]>([]);
  const [customizations, setCustomizations] = useState<Record<string, unknown>>({});
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset route draft before loading the next document
    setShowLoading(true);
    setInstances([]);
    setCustomizations({});
    setIsLoaded(false);

    (async () => {
      await loadCV(id);
      if (cancelled) return;
      setShowLoading(false);

      const currentCV = useBuilderDocumentStore.getState().currentCV;
      if (!currentCV?.sections) return;

      const nextInstances = currentCV.sections;
      const rawCustomizations = currentCV.customizations || {};
      const layout = rawCustomizations.layout as LayoutConfig | undefined;
      const nextCustomizations = layout?.placement
        ? { ...rawCustomizations, layout: migratePlacement(layout, nextInstances) }
        : rawCustomizations;

      setInstances(nextInstances);
      setCustomizations(nextCustomizations);
      setIsLoaded(true);
    })();

    return () => {
      cancelled = true;
    };
  }, [id, loadCV]);

  return {
    instances,
    customizations,
    setInstances,
    setCustomizations,
    isLoaded,
    showLoading,
  };
}
