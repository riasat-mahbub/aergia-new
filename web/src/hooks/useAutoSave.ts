import { useEffect, useRef, useCallback, useState } from "react";
import { updateCV } from "../lib/api/cvs";

interface AutoSaveOptions {
  cvId: string | undefined;
  data: Record<string, unknown>;
  debounceMs?: number;
  enabled?: boolean;
}

export function useAutoSave({ cvId, data, debounceMs = 3000, enabled = true }: AutoSaveOptions) {
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dataRef = useRef(data);
  const isSavingRef = useRef(false);
  const cvIdRef = useRef(cvId);

  useEffect(() => {
    dataRef.current = data;
    cvIdRef.current = cvId;
  }, [data, cvId]);

  const save = useCallback(async () => {
    if (!cvIdRef.current || isSavingRef.current) return;
    isSavingRef.current = true;
    setIsSaving(true);
    try {
      await updateCV(cvIdRef.current, dataRef.current);
      setLastSaved(new Date());
    } catch {
      // error handled by caller
    } finally {
      isSavingRef.current = false;
      setIsSaving(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled || !cvId) return;

    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    timerRef.current = setTimeout(() => {
      save();
    }, debounceMs);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [cvId, data, debounceMs, enabled, save]);

  return { isSaving, lastSaved, saveNow: save };
}
