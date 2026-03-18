import { useEffect, useRef, useCallback, useState } from "react";
import { updateCV } from "../lib/api/cvs";

interface AutoSaveOptions {
  cvId: string | undefined;
  data: Record<string, unknown>;
  debounceMs?: number;
  enabled?: boolean;
  onSaveComplete?: () => void;
  isPending?: () => boolean;
}

export function useAutoSave({ cvId, data, debounceMs = 3000, enabled = true, onSaveComplete, isPending }: AutoSaveOptions) {
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dataRef = useRef(data);
  const isSavingRef = useRef(false);
  const cvIdRef = useRef(cvId);
  const isMountedRef = useRef(true);
  const onSaveCompleteRef = useRef(onSaveComplete);
  onSaveCompleteRef.current = onSaveComplete;
  const isPendingRef = useRef(isPending);
  isPendingRef.current = isPending;

  useEffect(() => {
    dataRef.current = data;
    cvIdRef.current = cvId;
  }, [data, cvId]);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const save = useCallback(async () => {
    if (!cvIdRef.current || isSavingRef.current) return;
    if (isPendingRef.current?.()) return;
    isSavingRef.current = true;
    setIsSaving(true);
    try {
      await updateCV(cvIdRef.current, dataRef.current);
      if (!isMountedRef.current) return;
      setLastSaved(new Date());
      onSaveCompleteRef.current?.();
    } catch {
      // error handled by caller
    } finally {
      if (isMountedRef.current) {
        isSavingRef.current = false;
        setIsSaving(false);
      }
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
