import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Toast } from "@/shared/state/uiStore";
import {
  acceptTailoringDraft,
  cancelTailoringSession,
  createTailoringSession,
  getLatestTailoringSession,
  getTailoringSessionStatus,
  rejectTailoringDraft,
} from "../api/tailoring";
import type {
  TailoringSession,
  TailoringSessionResult,
  TailoringSessionStatusResponse,
} from "../types";
import {
  isTerminalTailoringStatus,
  terminalTailoringToast,
} from "../domain/tailoringPresentation";

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
  };
}

function viewBelongsToRoute(view: TailoringSessionView, identity: RouteIdentity): boolean {
  return view.applicationId === identity.applicationId && view.routeGeneration === identity.generation;
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
          tailoringSession: {
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
          },
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
    if (actionLocksRef.current.has(lockKey)) return;
    actionLocksRef.current.add(lockKey);
    latestRequestRef.current += 1;
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
    } catch {
      if (isCurrentRoute(identity)) {
        addToast("Unable to create a local tailoring session", "error");
      }
    } finally {
      actionLocksRef.current.delete(lockKey);
      if (isCurrentRoute(identity)) {
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
    const lockKey = `cancel:${session.session_id}`;
    if (actionLocksRef.current.has(lockKey)) return;
    actionLocksRef.current.add(lockKey);
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
    } catch {
      if (isCurrentSession(identity, session.session_id)) {
        addToast("Unable to cancel the tailoring session", "error");
      }
    } finally {
      actionLocksRef.current.delete(lockKey);
    }
  }, [addToast, currentView.tailoringSession, isCurrentSession, routeIdentity, updateForSession]);

  const acceptDraft = useCallback(async () => {
    const identity = routeIdentity;
    const session = currentView.tailoringSession;
    if (
      !session
      || session.application_id !== identity.applicationId
      || !isCurrentSession(identity, session.session_id)
    ) return;
    const lockKey = `accept:${session.session_id}`;
    if (actionLocksRef.current.has(lockKey)) return;
    actionLocksRef.current.add(lockKey);
    try {
      await acceptTailoringDraft(session.session_id);
      if (!isCurrentSession(identity, session.session_id)) return;
      const currentStatus = await getTailoringSessionStatus(session.session_id);
      if (
        !isCurrentSession(identity, session.session_id)
        || currentStatus.session_id !== session.session_id
        || currentStatus.application_id !== identity.applicationId
      ) return;
      updateForSession(identity, session.session_id, (current) => ({
        ...current,
        tailoringStatus: currentStatus,
        tailoringResult: currentStatus.result,
      }));
      if (!isCurrentSession(identity, session.session_id)) return;
      await fetchApplication(identity.applicationId);
      if (isCurrentSession(identity, session.session_id)) {
        addToast("Tailored CV accepted and linked to this application", "success");
      }
    } catch {
      if (isCurrentSession(identity, session.session_id)) {
        addToast("The tailored draft could not be accepted; the application may have changed", "error");
      }
    } finally {
      actionLocksRef.current.delete(lockKey);
    }
  }, [
    addToast,
    currentView.tailoringSession,
    fetchApplication,
    isCurrentSession,
    routeIdentity,
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
    const lockKey = `reject:${session.session_id}`;
    if (actionLocksRef.current.has(lockKey)) return;
    actionLocksRef.current.add(lockKey);
    try {
      await rejectTailoringDraft(session.session_id);
      if (!isCurrentSession(identity, session.session_id)) return;
      const currentStatus = await getTailoringSessionStatus(session.session_id);
      if (
        !isCurrentSession(identity, session.session_id)
        || currentStatus.session_id !== session.session_id
        || currentStatus.application_id !== identity.applicationId
      ) return;
      updateForSession(identity, session.session_id, (current) => ({
        ...current,
        tailoringStatus: currentStatus,
        tailoringResult: currentStatus.result,
      }));
      if (isCurrentSession(identity, session.session_id)) addToast("Tailored draft rejected", "info");
    } catch {
      if (isCurrentSession(identity, session.session_id)) {
        addToast("Unable to reject the tailored draft", "error");
      }
    } finally {
      actionLocksRef.current.delete(lockKey);
    }
  }, [
    addToast,
    currentView.tailoringSession,
    isCurrentSession,
    routeIdentity,
    updateForSession,
  ]);

  return {
    tailoringSession: currentView.tailoringSession,
    tailoringStarting: currentView.tailoringStarting,
    tailoringStatus: currentView.tailoringStatus,
    tailoringResult: currentView.tailoringResult,
    promptCopied: currentView.promptCopied,
    startTailoring,
    copyPrompt,
    cancelTailoring,
    acceptDraft,
    rejectDraft,
  };
}
