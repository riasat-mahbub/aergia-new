import { useCallback, useEffect, useRef, useState } from "react";
import { useBlocker } from "react-router-dom";
import type { SectionInstance } from "@/lib/cv/types";

export interface BuilderSaveData {
  sections: SectionInstance[];
  customizations: Record<string, unknown>;
}

interface UseUnsavedChangesOptions {
  enabled: boolean;
  getPendingSaveData: () => BuilderSaveData;
  save: (data: BuilderSaveData) => Promise<void>;
}

export function useUnsavedChanges({
  enabled,
  getPendingSaveData,
  save,
}: UseUnsavedChangesOptions) {
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const dirtyRef = useRef(false);

  const markDirty = useCallback(() => {
    dirtyRef.current = true;
    setHasUnsavedChanges(true);
  }, []);

  const markClean = useCallback(() => {
    dirtyRef.current = false;
    setHasUnsavedChanges(false);
  }, []);

  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      enabled &&
      dirtyRef.current &&
      currentLocation.pathname !== nextLocation.pathname,
  );

  useEffect(() => {
    if (blocker.state !== "blocked") return;
    (async () => {
      try {
        await save(getPendingSaveData());
      } finally {
        markClean();
        blocker.proceed();
      }
    })();
  }, [blocker, getPendingSaveData, markClean, save]);

  useEffect(() => {
    if (!dirtyRef.current) return;
    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, []);

  return { hasUnsavedChanges, markDirty, markClean };
}
