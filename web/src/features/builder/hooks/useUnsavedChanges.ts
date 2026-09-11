import { useCallback, useEffect, useRef, useState } from "react";
import { useBlocker } from "@tanstack/react-router";
import type { Customizations, SectionInstance } from "@/shared/cv/schema";

export interface BuilderSaveData {
  sections: SectionInstance[];
  customizations: Customizations;
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
    dirtyRef.current = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset dirty state when the route document changes
    setHasUnsavedChanges(false);
  }, [resetKey]);

  const blocker = useBlocker({
    withResolver: true,
    enableBeforeUnload: () => enabled && dirtyRef.current,
    shouldBlockFn: ({ current, next }) =>
      enabled && dirtyRef.current && current.pathname !== next.pathname,
  });

  useEffect(() => {
    if (blocker.status !== "blocked") return;
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

  return { hasUnsavedChanges, markDirty, markClean };
}
