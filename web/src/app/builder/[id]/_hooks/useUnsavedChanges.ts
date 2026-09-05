import { useCallback, useEffect, useRef, useState } from "react";
import { useBlocker } from "@/lib/routerCompat";
import type { SectionInstance } from "@/lib/cv/schema";

export interface BuilderSaveData {
  sections: SectionInstance[];
  customizations: Record<string, unknown>;
}

interface UseUnsavedChangesOptions {
  enabled: boolean;
  resetKey?: string;
  getPendingSaveData: () => BuilderSaveData;
  save: (data: BuilderSaveData) => Promise<void>;
}

export function useUnsavedChanges({
  enabled,
  resetKey,
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

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset dirty state when the route document changes
    dirtyRef.current = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset dirty state when the route document changes
    setHasUnsavedChanges(false);
  }, [resetKey]);

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
        markClean();
        blocker.proceed();
      } catch {
        blocker.reset();
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
