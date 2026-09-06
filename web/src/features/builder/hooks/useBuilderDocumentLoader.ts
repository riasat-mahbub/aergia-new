import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import type { SectionInstance } from "@/shared/cv/schema";
import type { LayoutConfig } from "@/shared/cv/placement";
import { migratePlacement } from "@/shared/cv/placement";
import { useBuilderDocumentStore } from "../state/builderDocumentStore";

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
  retry: () => void;
}

/** Loads one route document and normalizes legacy placement before editing starts. */
export function useBuilderDocumentLoader({ id, loadCV }: UseBuilderDocumentLoaderOptions): BuilderDocumentDraft {
  const [showLoading, setShowLoading] = useState(true);
  const [instances, setInstances] = useState<SectionInstance[]>([]);
  const [customizations, setCustomizations] = useState<Record<string, unknown>>({});
  const [isLoaded, setIsLoaded] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

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
  }, [id, loadCV, reloadKey]);

  return {
    instances,
    customizations,
    setInstances,
    setCustomizations,
    isLoaded,
    showLoading,
    retry: () => setReloadKey((value) => value + 1),
  };
}
