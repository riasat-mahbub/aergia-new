import { useCallback, useEffect, useRef, useState } from "react";
import { getApplication, recomputeApplicationRelevance } from "@/features/applications";
import type { Application } from "@/features/applications";
import { applicationMatchesCv, applicationRelevance } from "../domain/applicationRelevance";

interface UseBuilderApplicationContextOptions {
  applicationId: string | null;
  cvId: string;
}

export function useBuilderApplicationContext({
  applicationId,
  cvId,
}: UseBuilderApplicationContextOptions) {
  const [applicationContext, setApplicationContext] = useState<Application | null>(null);
  const [relevanceRefreshing, setRelevanceRefreshing] = useState(false);
  const [relevanceRefreshError, setRelevanceRefreshError] = useState(false);
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

  const refreshApplicationRelevance = useCallback(async () => {
    const linkedApplication = applicationRef.current;
    if (!linkedApplication) return;
    setRelevanceRefreshing(true);
    setRelevanceRefreshError(false);
    try {
      const refreshed = await recomputeApplicationRelevance(linkedApplication.id);
      if (refreshed.cv_id === cvId) {
        applicationRef.current = refreshed;
        setApplicationContext(refreshed);
      }
    } catch {
      // Relevance refresh is best effort; the saved CV remains authoritative.
      setRelevanceRefreshError(true);
    } finally {
      setRelevanceRefreshing(false);
    }
  }, [cvId]);

  return {
    applicationContext,
    relevance: applicationRelevance(applicationContext),
    relevanceRefreshing,
    relevanceRefreshError,
    refreshApplicationRelevance,
  };
}
