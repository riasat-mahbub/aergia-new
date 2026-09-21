import { useCallback, useEffect, useRef, useState } from "react";
import { getApplication, scanApplication } from "@/features/applications";
import type { Application } from "@/features/applications";
import { applicationMatchesCv } from "../domain/applicationRelevance";

interface UseBuilderApplicationContextOptions {
  applicationId: string | null;
  cvId: string;
}

export function useBuilderApplicationContext({
  applicationId,
  cvId,
}: UseBuilderApplicationContextOptions) {
  const [applicationContext, setApplicationContext] = useState<Application | null>(null);
  const [scannerRefreshing, setScannerRefreshing] = useState(false);
  const [scannerRefreshError, setScannerRefreshError] = useState(false);
  const applicationRef = useRef<Application | null>(null);

  useEffect(() => {
    applicationRef.current = applicationContext;
  }, [applicationContext]);

  useEffect(() => {
    let cancelled = false;
    // Reset stale application context whenever either route resource changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset stale route context before loading the next resource
    setApplicationContext(null);
    applicationRef.current = null;
    if (!applicationId || !cvId) return () => { cancelled = true; };

    (async () => {
      try {
        const application = await getApplication(applicationId);
        if (!cancelled && applicationMatchesCv(application, cvId)) {
          setApplicationContext(application);
        }
      } catch {
        // Invalid or cross-resource application IDs leave the ordinary builder unchanged.
      }
    })();

    return () => { cancelled = true; };
  }, [applicationId, cvId]);

  const refreshApplicationAnalysis = useCallback(async () => {
    const linkedApplication = applicationRef.current;
    if (!linkedApplication) return;
    setScannerRefreshError(false);
    try {
      // Saving a CV invalidates its scanner result. Refresh the application
      // status here without automatically starting an expensive scan.
      const refreshed = await getApplication(linkedApplication.id);
      if (refreshed.cv_id === cvId) {
        applicationRef.current = refreshed;
        setApplicationContext(refreshed);
      }
    } catch {
      setScannerRefreshError(true);
    }
  }, [cvId]);

  const runScanner = useCallback(async () => {
    const linkedApplication = applicationRef.current;
    if (!linkedApplication?.cv_id) return;
    setScannerRefreshing(true);
    setScannerRefreshError(false);
    try {
      const refreshed = await scanApplication(linkedApplication.id);
      if (refreshed.cv_id === cvId) {
        applicationRef.current = refreshed;
        setApplicationContext(refreshed);
      }
    } catch {
      setScannerRefreshError(true);
      throw new Error("scanner request failed");
    } finally {
      setScannerRefreshing(false);
    }
  }, [cvId]);

  return {
    applicationContext,
    scannerResult: applicationContext?.scanner_result ?? null,
    scannerStatus: applicationContext?.scanner_status ?? (applicationContext?.scanner_result ? "current" : "not_scanned"),
    scannerRefreshing,
    scannerRefreshError,
    refreshApplicationAnalysis,
    runScanner,
  };
}
