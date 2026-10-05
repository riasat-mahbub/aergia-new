import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Toast } from "@/shared/state/uiStore";
import {
  acceptTailoringDraft,
  cancelTailoringSession,
  createTailoringSession,
  getLatestTailoringSession,
  getTailoringSessionStatus,
  reevaluateTailoringDraft,
  rejectTailoringDraft,
} from "../api/tailoring";
import type {
  TailoringSession,
  TailoringSessionResult,
  TailoringSessionStatusResponse,
} from "../types";
import {
  isTerminalTailoringStatus,
  tailoringErrorCode,
  tailoringErrorDetail,
  terminalTailoringToast,
} from "../domain/tailoringPresentation";

type TailoringOwnerAction = "cancel" | "reevaluate" | "accept" | "discard";

interface UseTailoringSessionOptions {
  applicationId: string;
  fetchApplication: (id: string) => Promise<unknown>;
  addToast: (message: string, type?: Toast["type"]) => void;
}

interface RouteIdentity {
  applicationId: string;
  generation: number;
}

interface TailoringSessionView {
  applicationId: string;
  routeGeneration: number;
  tailoringSession: TailoringSession | null;
  tailoringStarting: boolean;
  tailoringStatus: TailoringSessionStatusResponse | null;
  tailoringResult: TailoringSessionResult | null;
  promptCopied: boolean;
  tailoringAction: TailoringOwnerAction | null;
  tailoringActionError: string | null;
}

function emptyView(identity: RouteIdentity): TailoringSessionView {
  return {
    applicationId: identity.applicationId,
    routeGeneration: identity.generation,
    tailoringSession: null,
    tailoringStarting: false,
    tailoringStatus: null,
    tailoringResult: null,
    promptCopied: false,
    tailoringAction: null,
    tailoringActionError: null,
  };
}

function viewBelongsToRoute(view: TailoringSessionView, identity: RouteIdentity): boolean {
  return view.applicationId === identity.applicationId && view.routeGeneration === identity.generation;
}

function hydratedSession(status: TailoringSessionStatusResponse): TailoringSession {
  return {
    protocol_version: status.protocol_version,
    session_id: status.session_id,
    application_id: status.application_id,
    source_cv_id: status.source_cv_id,
    cv_id: status.cv_id,
    code: "",
    session_url: "",
    skill_url: "",
    prompt: "This tailoring session is already in progress or awaiting your review.",
    status: "created",
    expires_at: status.expires_at,
  };
}

export function useTailoringSession({
  applicationId,
  fetchApplication,
  addToast,
}: UseTailoringSessionOptions) {
  const [routeIdentity, setRouteIdentity] = useState<RouteIdentity>(() => ({ applicationId, generation: 0 }));
  if (routeIdentity.applicationId !== applicationId) {
    setRouteIdentity({ applicationId, generation: routeIdentity.generation + 1 });
  }
  const routeIdentityRef = useRef(routeIdentity);
  const mountedRef = useRef(false);
  useLayoutEffect(() => {
    routeIdentityRef.current = routeIdentity;
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, [routeIdentity]);

  const [view, setView] = useState<TailoringSessionView>(() => emptyView(routeIdentity));
  const viewRef = useRef(view);
  const latestRequestRef = useRef(0);
  const actionLocksRef = useRef(new Set<string>());
  const inFlightPollsRef = useRef(new Set<string>());
  const toastedStatusesRef = useRef(new Set<string>());

  const isCurrentRoute = useCallback((identity: RouteIdentity) => {
    const current = routeIdentityRef.current;
    return mountedRef.current
      && current.applicationId === identity.applicationId
      && current.generation === identity.generation;
  }, []);

  const currentView = viewBelongsToRoute(view, routeIdentity) ? view : emptyView(routeIdentity);

  const updateForRoute = useCallback((
    identity: RouteIdentity,
    update: (current: TailoringSessionView) => TailoringSessionView,
  ) => {
    if (!isCurrentRoute(identity)) return;
    const previous = viewRef.current;
    const current = viewBelongsToRoute(previous, identity) ? previous : emptyView(identity);
    const next = update(current);
    if (next === current) return;
    viewRef.current = next;
    setView(next);
  }, [isCurrentRoute]);

  const updateForSession = useCallback((
    identity: RouteIdentity,
    sessionId: string,
    update: (current: TailoringSessionView) => TailoringSessionView,
  ) => {
    updateForRoute(identity, (current) => (
      current.tailoringSession?.session_id === sessionId
        ? update(current)
        : current
    ));
  }, [updateForRoute]);

  const isCurrentSession = useCallback((identity: RouteIdentity, sessionId: string) => {
    if (!isCurrentRoute(identity)) return false;
    const current = viewRef.current;
    return viewBelongsToRoute(current, identity)
      && current.tailoringSession?.session_id === sessionId
      && current.tailoringSession.application_id === identity.applicationId;
  }, [isCurrentRoute]);

  const beginOwnerAction = useCallback((
    identity: RouteIdentity,
    sessionId: string,
    action: TailoringOwnerAction,
  ) => {
    const lockKey = `owner:${sessionId}`;
    const latest = viewRef.current;
    if (
      !isCurrentSession(identity, sessionId)
      || actionLocksRef.current.has(lockKey)
      || (viewBelongsToRoute(latest, identity) && (latest.tailoringAction !== null || latest.tailoringStarting))
    ) return false;
    actionLocksRef.current.add(lockKey);
    updateForSession(identity, sessionId, (current) => ({
      ...current,
      tailoringAction: action,
      tailoringActionError: null,
    }));
    return true;
  }, [isCurrentSession, updateForSession]);

  const finishOwnerAction = useCallback((identity: RouteIdentity, sessionId: string) => {
    actionLocksRef.current.delete(`owner:${sessionId}`);
    updateForSession(identity, sessionId, (current) => (
      current.tailoringAction === null
        ? current
        : { ...current, tailoringAction: null }
    ));
  }, [updateForSession]);

  const setOwnerActionError = useCallback((
    identity: RouteIdentity,
    sessionId: string,
    message: string,
  ) => {
    updateForSession(identity, sessionId, (current) => ({
      ...current,
      tailoringActionError: message,
    }));
  }, [updateForSession]);

  const refreshSessionStatus = useCallback(async (
    identity: RouteIdentity,
    sessionId: string,
  ): Promise<TailoringSessionStatusResponse | null> => {
    try {
      const status = await getTailoringSessionStatus(sessionId);
      if (
        !isCurrentSession(identity, sessionId)
        || status.session_id !== sessionId
        || status.application_id !== identity.applicationId
      ) return null;
      updateForSession(identity, sessionId, (current) => ({
        ...current,
        tailoringStatus: status,
        tailoringResult: status.result,
      }));
      return status;
    } catch {
      return null;
    }
  }, [isCurrentSession, updateForSession]);

  useEffect(() => {
    const identity = routeIdentity;
    const requestGeneration = ++latestRequestRef.current;
    let cancelled = false;

    void getLatestTailoringSession(identity.applicationId).then((status) => {
      if (
        cancelled
        || !isCurrentRoute(identity)
        || latestRequestRef.current !== requestGeneration
        || status.application_id !== identity.applicationId
      ) return;

      updateForRoute(identity, (current) => {
        // Starting a new session invalidates hydration as well as clearing the
        // old view. Keep this content check as a second guard if requests race.
        if (current.tailoringSession?.code.trim()) return current;
        return {
          ...current,
          tailoringSession: hydratedSession(status),
          tailoringStatus: status,
          tailoringResult: status.result,
          promptCopied: false,
        };
      });
    }).catch(() => {
      // A new application normally has no tailoring session yet.
    });

    return () => { cancelled = true; };
  }, [isCurrentRoute, routeIdentity, updateForRoute]);

  const activeSession = currentView.tailoringSession;
  const activeStatus = currentView.tailoringStatus;
  const activeStatusIsTerminal = isTerminalTailoringStatus(activeStatus?.status);
  const activeStatusApplicationId = activeStatus?.application_id;

  useEffect(() => {
    const identity = routeIdentity;
    const session = activeSession;
    const sessionId = session?.session_id;
    if (
      !sessionId
      || session?.application_id !== identity.applicationId
      || (activeStatusApplicationId && activeStatusApplicationId !== identity.applicationId)
      || activeStatusIsTerminal
    ) return;

    let cancelled = false;
    let timer: number | undefined;
    const poll = async () => {
      if (cancelled || !isCurrentSession(identity, sessionId)) return;

      // A remounted effect can encounter an older request still settling.
      // Wait for that request instead of issuing an overlapping poll.
      if (inFlightPollsRef.current.has(sessionId)) {
        timer = window.setTimeout(() => { void poll(); }, 250);
        return;
      }

      inFlightPollsRef.current.add(sessionId);
      try {
        const status = await getTailoringSessionStatus(sessionId);
        if (
          cancelled
          || !isCurrentSession(identity, sessionId)
          || status.application_id !== identity.applicationId
          || status.session_id !== sessionId
        ) return;

        updateForSession(identity, sessionId, (current) => ({
          ...current,
          tailoringStatus: status,
          tailoringResult: status.result,
        }));

        const toast = terminalTailoringToast(status.status);
        const toastKey = `${sessionId}:${status.status}`;
        if (
          toast
          && !toastedStatusesRef.current.has(toastKey)
          && isCurrentSession(identity, sessionId)
        ) {
          toastedStatusesRef.current.add(toastKey);
          addToast(toast.message, toast.type);
        }

        if (status.status === "accepted" && isCurrentSession(identity, sessionId)) {
          await fetchApplication(identity.applicationId);
        }
      } catch {
        // Keep the last known session state visible while the user can retry.
      } finally {
        inFlightPollsRef.current.delete(sessionId);
        const latest = viewRef.current;
        if (
          !cancelled
          && isCurrentSession(identity, sessionId)
          && viewBelongsToRoute(latest, identity)
          && !isTerminalTailoringStatus(latest.tailoringStatus?.status)
        ) {
          timer = window.setTimeout(() => { void poll(); }, 3000);
        }
      }
    };

    void poll();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [
    activeSession,
    activeStatusApplicationId,
    activeStatusIsTerminal,
    addToast,
    fetchApplication,
    isCurrentSession,
    routeIdentity,
    updateForSession,
  ]);

  const startTailoring = useCallback(async () => {
    const identity = routeIdentity;
    if (!isCurrentRoute(identity)) return;
    const lockKey = `start:${identity.applicationId}`;
    const latest = viewRef.current;
    if (
      actionLocksRef.current.has(lockKey)
      || (viewBelongsToRoute(latest, identity) && (latest.tailoringAction !== null || latest.tailoringStarting))
    ) return;
    actionLocksRef.current.add(lockKey);
    const requestGeneration = ++latestRequestRef.current;
    const canApplyStartResult = () => {
      if (!isCurrentRoute(identity) || latestRequestRef.current !== requestGeneration) return false;
      const current = viewRef.current;
      return !viewBelongsToRoute(current, identity) || !current.tailoringSession?.code.trim();
    };
    updateForRoute(identity, (current) => ({
      ...emptyView(identity),
      tailoringStarting: true,
      // Do not discard a second click or route transition through a stale view.
      applicationId: current.applicationId,
    }));

    try {
      const session = await createTailoringSession(identity.applicationId);
      if (
        !isCurrentRoute(identity)
        || session.application_id !== identity.applicationId
      ) return;
      updateForRoute(identity, (current) => ({
        ...current,
        tailoringSession: session,
        tailoringStatus: null,
        tailoringResult: null,
        promptCopied: false,
      }));
      if (isCurrentRoute(identity)) addToast("Tailoring session created", "info");
    } catch (error) {
      if (!canApplyStartResult()) return;
      const message = tailoringErrorDetail(
        error,
        "Unable to start tailoring. Resolve or discard any pending draft, then try again.",
      );

      if (tailoringErrorCode(error) === "session_in_progress") {
        try {
          const status = await getLatestTailoringSession(identity.applicationId);
          if (!canApplyStartResult()) return;
          if (status.application_id !== identity.applicationId) {
            updateForRoute(identity, (current) => ({ ...current, tailoringActionError: message }));
            addToast(message, "error");
            return;
          }
          updateForRoute(identity, (current) => {
            if (current.tailoringSession?.code.trim()) return current;
            return {
              ...current,
              tailoringSession: hydratedSession(status),
              tailoringStatus: status,
              tailoringResult: status.result,
              promptCopied: false,
              tailoringActionError: message,
            };
          });
          return;
        } catch {
          if (!canApplyStartResult()) return;
        }
      }

      if (!canApplyStartResult()) return;
      updateForRoute(identity, (current) => ({ ...current, tailoringActionError: message }));
      addToast(message, "error");
    } finally {
      actionLocksRef.current.delete(lockKey);
      if (isCurrentRoute(identity) && latestRequestRef.current === requestGeneration) {
        updateForRoute(identity, (current) => ({ ...current, tailoringStarting: false }));
      }
    }
  }, [addToast, isCurrentRoute, routeIdentity, updateForRoute]);

  const copyPrompt = useCallback(async () => {
    const identity = routeIdentity;
    const session = currentView.tailoringSession;
    if (
      !isCurrentRoute(identity)
      || !session
      || session.application_id !== identity.applicationId
      || !session.code.trim()
      || !session.prompt.trim()
    ) return;

    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(session.prompt);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = session.prompt;
        textarea.setAttribute("readonly", "true");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }
      if (isCurrentSession(identity, session.session_id)) {
        updateForSession(identity, session.session_id, (current) => ({ ...current, promptCopied: true }));
        addToast("Prompt copied — paste it into your coding agent", "info");
      }
    } catch {
      if (isCurrentSession(identity, session.session_id)) {
        addToast("Unable to copy the tailoring prompt", "error");
      }
    }
  }, [
    addToast,
    currentView.tailoringSession,
    isCurrentRoute,
    isCurrentSession,
    routeIdentity,
    updateForSession,
  ]);

  const cancelTailoring = useCallback(async () => {
    const identity = routeIdentity;
    const session = currentView.tailoringSession;
    if (
      !session
      || session.application_id !== identity.applicationId
      || !isCurrentSession(identity, session.session_id)
    ) return;
    if (!beginOwnerAction(identity, session.session_id, "cancel")) return;
    try {
      const status = await cancelTailoringSession(session.session_id);
      if (
        !isCurrentSession(identity, session.session_id)
        || status.session_id !== session.session_id
        || status.application_id !== identity.applicationId
      ) return;
      updateForSession(identity, session.session_id, (current) => ({
        ...current,
        tailoringStatus: status,
        tailoringResult: status.result,
      }));
      const toastKey = `${session.session_id}:cancelled`;
      toastedStatusesRef.current.add(toastKey);
      if (isCurrentSession(identity, session.session_id)) addToast("Tailoring session cancelled", "info");
    } catch (error) {
      if (isCurrentSession(identity, session.session_id)) {
        const message = tailoringErrorDetail(error, "Unable to cancel the tailoring session.");
        setOwnerActionError(identity, session.session_id, message);
        addToast(message, "error");
      }
    } finally {
      finishOwnerAction(identity, session.session_id);
    }
  }, [
    addToast,
    beginOwnerAction,
    currentView.tailoringSession,
    finishOwnerAction,
    isCurrentSession,
    routeIdentity,
    setOwnerActionError,
    updateForSession,
  ]);

  const reevaluateDraft = useCallback(async () => {
    const identity = routeIdentity;
    const session = currentView.tailoringSession;
    const status = currentView.tailoringStatus;
    const draftReview = status?.draft_review;
    const revision = draftReview?.cv_revision;
    if (
      !session
      || session.application_id !== identity.applicationId
      || !isCurrentSession(identity, session.session_id)
    ) return;
    if (
      status?.protocol_version !== 10
      || draftReview?.state !== "needs_reevaluation"
      || typeof revision !== "number"
      || !Number.isInteger(revision)
    ) {
      setOwnerActionError(identity, session.session_id, "The saved draft revision is unavailable. Reload this application before reevaluating.");
      return;
    }
    if (!beginOwnerAction(identity, session.session_id, "reevaluate")) return;

    try {
      const response = await reevaluateTailoringDraft(session.session_id, { expected_cv_revision: revision });
      if (
        !isCurrentSession(identity, session.session_id)
        || response.session_id !== session.session_id
        || response.application_id !== identity.applicationId
        || response.draft_cv_id !== (status.draft_cv_id ?? currentView.tailoringResult?.draft_cv_id)
      ) return;
      if (response.draft_review.state !== "current") {
        setOwnerActionError(identity, session.session_id, "The draft changed while it was being reviewed. Reload the saved draft and try again.");
        return;
      }
      updateForSession(identity, session.session_id, (current) => ({
        ...current,
        tailoringStatus: current.tailoringStatus
          ? {
              ...current.tailoringStatus,
              draft_cv_id: response.draft_cv_id,
              draft_review: response.draft_review,
              updated_at: new Date().toISOString(),
            }
          : current.tailoringStatus,
      }));
      try {
        await fetchApplication(identity.applicationId);
      } catch {
        if (isCurrentSession(identity, session.session_id)) {
          setOwnerActionError(identity, session.session_id, "The draft review is current, but the application could not refresh. Reload to see the latest details.");
        }
      }
      if (isCurrentSession(identity, session.session_id)) addToast("Draft review updated", "success");
    } catch (error) {
      if (isCurrentSession(identity, session.session_id)) {
        await refreshSessionStatus(identity, session.session_id);
        if (isCurrentSession(identity, session.session_id)) {
          const message = tailoringErrorDetail(error, "Unable to reevaluate the saved draft. Save any edits and try again.");
          setOwnerActionError(identity, session.session_id, message);
          addToast(message, "error");
        }
      }
    } finally {
      finishOwnerAction(identity, session.session_id);
    }
  }, [
    addToast,
    beginOwnerAction,
    currentView.tailoringResult?.draft_cv_id,
    currentView.tailoringSession,
    currentView.tailoringStatus,
    fetchApplication,
    finishOwnerAction,
    isCurrentSession,
    refreshSessionStatus,
    routeIdentity,
    setOwnerActionError,
    updateForSession,
  ]);

  const acceptDraft = useCallback(async () => {
    const identity = routeIdentity;
    const session = currentView.tailoringSession;
    const status = currentView.tailoringStatus;
    if (
      !session
      || session.application_id !== identity.applicationId
      || !isCurrentSession(identity, session.session_id)
    ) return;
    const protocolVersion = status?.protocol_version ?? session.protocol_version;
    let request: { expected_cv_revision: number; candidate_hash: string } | undefined;
    if (protocolVersion >= 10) {
      const review = status?.draft_review;
      if (
        review?.state !== "current"
        || typeof review.cv_revision !== "number"
        || !Number.isInteger(review.cv_revision)
        || typeof review.candidate_hash !== "string"
        || !/^[0-9a-f]{64}$/.test(review.candidate_hash)
      ) {
        setOwnerActionError(identity, session.session_id, "Reevaluate the saved draft before accepting it.");
        return;
      }
      request = { expected_cv_revision: review.cv_revision, candidate_hash: review.candidate_hash };
    }
    if (!beginOwnerAction(identity, session.session_id, "accept")) return;
    try {
      const accepted = await acceptTailoringDraft(session.session_id, request);
      if (!isCurrentSession(identity, session.session_id)) return;
      if (accepted.session_id !== session.session_id || accepted.application_id !== identity.applicationId) return;
      const currentStatus = await refreshSessionStatus(identity, session.session_id);
      if (!currentStatus && isCurrentSession(identity, session.session_id)) {
        updateForSession(identity, session.session_id, (current) => current.tailoringStatus
          ? {
              ...current,
              tailoringStatus: {
                ...current.tailoringStatus,
                status: "accepted",
                draft_cv_id: accepted.draft_cv_id,
                cv_id: accepted.cv_id,
                reviewed_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
            }
          : current);
      }
      if (!isCurrentSession(identity, session.session_id)) return;
      try {
        await fetchApplication(identity.applicationId);
      } catch {
        if (isCurrentSession(identity, session.session_id)) {
          setOwnerActionError(identity, session.session_id, "The draft was accepted, but the application could not refresh. Reload to see the linked CV.");
        }
      }
      if (isCurrentSession(identity, session.session_id)) {
        addToast("Tailored CV accepted and linked to this application", "success");
      }
    } catch (error) {
      if (isCurrentSession(identity, session.session_id)) {
        await refreshSessionStatus(identity, session.session_id);
        if (isCurrentSession(identity, session.session_id)) {
          const message = tailoringErrorDetail(error, "The tailored draft could not be accepted. Review the current status, then retry or discard it.");
          setOwnerActionError(identity, session.session_id, message);
          addToast(message, "error");
        }
      }
    } finally {
      finishOwnerAction(identity, session.session_id);
    }
  }, [
    addToast,
    beginOwnerAction,
    currentView.tailoringSession,
    currentView.tailoringStatus,
    finishOwnerAction,
    fetchApplication,
    isCurrentSession,
    refreshSessionStatus,
    routeIdentity,
    setOwnerActionError,
    updateForSession,
  ]);

  const rejectDraft = useCallback(async () => {
    const identity = routeIdentity;
    const session = currentView.tailoringSession;
    if (
      !session
      || session.application_id !== identity.applicationId
      || !isCurrentSession(identity, session.session_id)
    ) return;
    if (!beginOwnerAction(identity, session.session_id, "discard")) return;
    try {
      const discarded = await rejectTailoringDraft(session.session_id);
      if (!isCurrentSession(identity, session.session_id)) return;
      if (discarded.session_id !== session.session_id || discarded.application_id !== identity.applicationId) return;
      updateForSession(identity, session.session_id, (current) => current.tailoringStatus
        ? {
            ...current,
            tailoringStatus: {
              ...current.tailoringStatus,
              status: "rejected",
              draft_cv_id: null,
              cv_id: discarded.cv_id,
              reviewed_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          }
        : current);
      const currentStatus = await refreshSessionStatus(identity, session.session_id);
      if (
        currentStatus !== null
        && (!isCurrentSession(identity, session.session_id)
          || currentStatus.session_id !== session.session_id
          || currentStatus.application_id !== identity.applicationId)
      ) return;
      if (!isCurrentSession(identity, session.session_id)) return;
      try {
        await fetchApplication(identity.applicationId);
      } catch {
        if (isCurrentSession(identity, session.session_id)) {
          setOwnerActionError(identity, session.session_id, "The draft was discarded, but the application could not refresh. Reload to see the latest details.");
        }
      }
      if (isCurrentSession(identity, session.session_id)) addToast("Tailored draft discarded. You can start a new session.", "info");
    } catch (error) {
      if (isCurrentSession(identity, session.session_id)) {
        await refreshSessionStatus(identity, session.session_id);
        if (isCurrentSession(identity, session.session_id)) {
          const message = tailoringErrorDetail(error, "Unable to discard the tailored draft. Reload the session and try again.");
          setOwnerActionError(identity, session.session_id, message);
          addToast(message, "error");
        }
      }
    } finally {
      finishOwnerAction(identity, session.session_id);
    }
  }, [
    addToast,
    beginOwnerAction,
    currentView.tailoringSession,
    fetchApplication,
    finishOwnerAction,
    isCurrentSession,
    refreshSessionStatus,
    routeIdentity,
    setOwnerActionError,
    updateForSession,
  ]);

  return {
    tailoringSession: currentView.tailoringSession,
    tailoringStarting: currentView.tailoringStarting,
    tailoringStatus: currentView.tailoringStatus,
    tailoringResult: currentView.tailoringResult,
    promptCopied: currentView.promptCopied,
    tailoringAction: currentView.tailoringAction,
    tailoringActionError: currentView.tailoringActionError,
    startTailoring,
    copyPrompt,
    cancelTailoring,
    reevaluateDraft,
    acceptDraft,
    rejectDraft,
  };
}
