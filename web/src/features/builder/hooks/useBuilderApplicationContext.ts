import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { getApplication, scanApplication } from "@/features/applications";
import type { Application } from "@/features/applications";
import {
  getTailoringDraftContext,
} from "@/features/tailoring";
import type {
  TailoringDraftContextResponse,
  TailoringReevaluateResponse,
} from "@/features/tailoring";
import { applicationMatchesCv } from "../domain/applicationRelevance";

interface UseBuilderApplicationContextOptions {
  applicationId: string | null;
  cvId: string;
}

type ContextState = {
  resourceKey: string;
  kind: "loading" | "ordinary" | "pending" | "pending_unavailable" | "error";
  applicationContext: Application | null;
  pendingDraftContext: TailoringDraftContextResponse | null;
  pendingDraftApplicationId: string | null;
  error: string | null;
  draftContextRefreshFailed: boolean;
};

interface ActiveRouteResource {
  resourceKey: string;
  generation: number;
  mounted: boolean;
}

interface ScannerState {
  resourceKey: string;
  refreshing: boolean;
  error: boolean;
}

const NOT_FOUND_MESSAGE = "This tailoring draft is no longer available. Return to the application review to discard it or start again.";
const CONTEXT_ERROR_MESSAGE = "The draft review could not be loaded. Retry by reopening the builder.";

function responseStatus(error: unknown): number | null {
  if (!error || typeof error !== "object") return null;
  const response = (error as { response?: { status?: unknown } }).response;
  return typeof response?.status === "number" ? response.status : null;
}

export function useBuilderApplicationContext({
  applicationId,
  cvId,
}: UseBuilderApplicationContextOptions) {
  const resourceKey = `${cvId}:${applicationId ?? ""}`;
  const [contextState, setContextState] = useState<ContextState>({
    resourceKey: "",
    kind: "loading",
    applicationContext: null,
    pendingDraftContext: null,
    pendingDraftApplicationId: null,
    error: null,
    draftContextRefreshFailed: false,
  });
  const [scannerState, setScannerState] = useState<ScannerState>({
    resourceKey: "",
    refreshing: false,
    error: false,
  });
  const activeRouteRef = useRef<ActiveRouteResource>({ resourceKey: "", generation: 0, mounted: false });
  const applicationRef = useRef<Application | null>(null);
  const pendingDraftRef = useRef<TailoringDraftContextResponse | null>(null);

  useLayoutEffect(() => {
    const generation = activeRouteRef.current.generation + 1;
    activeRouteRef.current = { resourceKey, generation, mounted: true };
    return () => {
      if (activeRouteRef.current.generation === generation) {
        activeRouteRef.current = { resourceKey, generation: generation + 1, mounted: false };
      }
    };
  }, [resourceKey]);

  const isCurrentResource = useCallback((key: string, generation: number) => {
    const active = activeRouteRef.current;
    return active.mounted && active.resourceKey === key && active.generation === generation;
  }, []);

  useEffect(() => {
    const generation = activeRouteRef.current.generation;
    const isCurrent = () => isCurrentResource(resourceKey, generation);

    applicationRef.current = null;
    pendingDraftRef.current = null;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- clear the previous route resource before resolving its replacement
    setContextState({
      resourceKey,
      kind: "loading",
      applicationContext: null,
      pendingDraftContext: null,
      pendingDraftApplicationId: null,
      error: null,
      draftContextRefreshFailed: false,
    });
    setScannerState({ resourceKey, refreshing: false, error: false });

    if (!cvId) {
      setContextState({
        resourceKey,
        kind: "ordinary",
        applicationContext: null,
        pendingDraftContext: null,
        pendingDraftApplicationId: null,
        error: null,
        draftContextRefreshFailed: false,
      });
      return;
    }

    void (async () => {
      try {
        // A tailoring draft is intentionally unlinked. Its API context owns the
        // application identity and review data; the optional route search value
        // is not evidence that it belongs to that application.
        const draftContext = await getTailoringDraftContext(cvId);
        if (!isCurrent()) return;
        if (draftContext.draft_cv_id !== cvId) {
          setContextState({
            resourceKey,
            kind: "error",
            applicationContext: null,
            pendingDraftContext: null,
            pendingDraftApplicationId: null,
            error: CONTEXT_ERROR_MESSAGE,
            draftContextRefreshFailed: false,
          });
          return;
        }
        pendingDraftRef.current = draftContext;
        setContextState({
          resourceKey,
          kind: "pending",
          applicationContext: null,
          pendingDraftContext: draftContext,
          pendingDraftApplicationId: draftContext.application_id,
          error: null,
          draftContextRefreshFailed: false,
        });
        return;
      } catch (error) {
        if (!isCurrent()) return;
        if (responseStatus(error) !== 404) {
          setContextState({
            resourceKey,
            kind: "error",
            applicationContext: null,
            pendingDraftContext: null,
            pendingDraftApplicationId: null,
            error: CONTEXT_ERROR_MESSAGE,
            draftContextRefreshFailed: false,
          });
          return;
        }
      }

      if (!applicationId) {
        setContextState({
          resourceKey,
          kind: "ordinary",
          applicationContext: null,
          pendingDraftContext: null,
          pendingDraftApplicationId: null,
          error: null,
          draftContextRefreshFailed: false,
        });
        return;
      }

      try {
        const application = await getApplication(applicationId);
        if (!isCurrent()) return;
        const matchingApplication = applicationMatchesCv(application, cvId) ? application : null;
        applicationRef.current = matchingApplication;
        setContextState({
          resourceKey,
          kind: "ordinary",
          applicationContext: matchingApplication,
          pendingDraftContext: null,
          pendingDraftApplicationId: null,
          error: null,
          draftContextRefreshFailed: false,
        });
      } catch {
        if (!isCurrent()) return;
        setContextState({
          resourceKey,
          kind: "ordinary",
          applicationContext: null,
          pendingDraftContext: null,
          pendingDraftApplicationId: null,
          error: null,
          draftContextRefreshFailed: false,
        });
      }
    })();

  }, [applicationId, cvId, isCurrentResource, resourceKey]);

  const refreshApplicationAnalysis = useCallback(async () => {
    const active = activeRouteRef.current;
    const generation = active.generation;
    if (!isCurrentResource(resourceKey, generation)) return;
    const pendingDraft = pendingDraftRef.current;
    if (pendingDraft?.draft_cv_id === cvId) {
      try {
        const refreshed = await getTailoringDraftContext(cvId);
        if (!isCurrentResource(resourceKey, generation)) return;
        if (
          refreshed.draft_cv_id !== cvId
          || refreshed.session_id !== pendingDraft.session_id
          || refreshed.application_id !== pendingDraft.application_id
        ) {
          pendingDraftRef.current = null;
          setContextState((current) => current.resourceKey !== resourceKey ? current : {
            ...current,
            kind: "pending_unavailable",
            applicationContext: null,
            pendingDraftContext: null,
            error: NOT_FOUND_MESSAGE,
            draftContextRefreshFailed: false,
          });
          throw new Error(NOT_FOUND_MESSAGE);
        }
        pendingDraftRef.current = refreshed;
        setContextState((current) => current.resourceKey !== resourceKey ? current : {
          ...current,
          kind: "pending",
          applicationContext: null,
          pendingDraftContext: refreshed,
          pendingDraftApplicationId: refreshed.application_id,
          error: null,
          draftContextRefreshFailed: false,
        });
      } catch (error) {
        if (!isCurrentResource(resourceKey, generation)) return;
        if (responseStatus(error) === 404) {
          pendingDraftRef.current = null;
          setContextState((current) => current.resourceKey !== resourceKey ? current : {
            ...current,
            kind: "pending_unavailable",
            applicationContext: null,
            pendingDraftContext: null,
            error: NOT_FOUND_MESSAGE,
            draftContextRefreshFailed: false,
          });
          throw new Error(NOT_FOUND_MESSAGE);
        } else {
          setContextState((current) => current.resourceKey !== resourceKey ? current : {
            ...current,
            draftContextRefreshFailed: true,
          });
          throw error;
        }
      }
      return;
    }

    const linkedApplication = applicationRef.current;
    if (!linkedApplication) return;
    setScannerState({ resourceKey, refreshing: false, error: false });
    try {
      // Saving a linked CV invalidates its scanner result. Refresh application
      // state without automatically starting another scan.
      const refreshed = await getApplication(linkedApplication.id);
      if (!isCurrentResource(resourceKey, generation)) return;
      if (applicationMatchesCv(refreshed, cvId)) {
        applicationRef.current = refreshed;
        setContextState((current) => current.resourceKey !== resourceKey ? current : {
          ...current,
          applicationContext: refreshed,
        });
      }
    } catch {
      if (isCurrentResource(resourceKey, generation)) {
        setScannerState({ resourceKey, refreshing: false, error: true });
      }
    }
  }, [cvId, isCurrentResource, resourceKey]);

  const runScanner = useCallback(async () => {
    const active = activeRouteRef.current;
    const generation = active.generation;
    if (!isCurrentResource(resourceKey, generation)) return;
    const linkedApplication = applicationRef.current;
    if (!linkedApplication?.cv_id || linkedApplication.cv_id !== cvId) return;
    setScannerState({ resourceKey, refreshing: true, error: false });
    try {
      const refreshed = await scanApplication(linkedApplication.id);
      if (isCurrentResource(resourceKey, generation) && applicationMatchesCv(refreshed, cvId)) {
        applicationRef.current = refreshed;
        setContextState((current) => current.resourceKey !== resourceKey ? current : {
          ...current,
          applicationContext: refreshed,
        });
      }
    } catch {
      if (isCurrentResource(resourceKey, generation)) {
        setScannerState({ resourceKey, refreshing: false, error: true });
      }
      throw new Error("scanner request failed");
    } finally {
      if (isCurrentResource(resourceKey, generation)) {
        setScannerState((current) => current.resourceKey === resourceKey
          ? { ...current, refreshing: false }
          : current);
      }
    }
  }, [cvId, isCurrentResource, resourceKey]);

  const applyPendingDraftReview = useCallback((response: TailoringReevaluateResponse) => {
    const active = activeRouteRef.current;
    if (!isCurrentResource(resourceKey, active.generation)) return false;
    const current = pendingDraftRef.current;
    if (
      !current
      || current.draft_cv_id !== cvId
      || response.draft_cv_id !== cvId
      || response.session_id !== current.session_id
      || response.application_id !== current.application_id
    ) return false;

    const refreshed: TailoringDraftContextResponse = {
      ...current,
      draft_review: response.draft_review,
    };
    pendingDraftRef.current = refreshed;
    setContextState((state) => state.resourceKey !== resourceKey || state.kind !== "pending"
      ? state
      : { ...state, pendingDraftContext: refreshed, error: null, draftContextRefreshFailed: false });
    return true;
  }, [cvId, isCurrentResource, resourceKey]);

  const currentState = contextState.resourceKey === resourceKey
    ? contextState
    : {
      resourceKey,
      kind: "loading" as const,
      applicationContext: null,
      pendingDraftContext: null,
      pendingDraftApplicationId: null,
      error: null,
      draftContextRefreshFailed: false,
    };
  const currentScannerState = scannerState.resourceKey === resourceKey
    ? scannerState
    : { resourceKey, refreshing: false, error: false };

  return {
    applicationContext: currentState.applicationContext,
    pendingDraftContext: currentState.pendingDraftContext,
    pendingDraftApplicationId: currentState.pendingDraftApplicationId,
    pendingDraftUnavailable: currentState.kind === "pending_unavailable",
    applicationContextError: currentState.error,
    applicationContextLoading: currentState.kind === "loading",
    draftContextRefreshFailed: currentState.draftContextRefreshFailed,
    scannerResult: currentState.applicationContext?.scanner_result ?? null,
    scannerStatus: currentState.applicationContext?.scanner_status ?? (currentState.applicationContext?.scanner_result ? "current" : "not_scanned"),
    scannerRefreshing: currentScannerState.refreshing,
    scannerRefreshError: currentScannerState.error,
    refreshApplicationAnalysis,
    runScanner,
    applyPendingDraftReview,
  };
}
