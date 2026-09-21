import { useCallback, useEffect, useRef, useState } from "react";
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

export function useTailoringSession({
  applicationId,
  fetchApplication,
  addToast,
}: UseTailoringSessionOptions) {
  const [tailoringSession, setTailoringSession] = useState<TailoringSession | null>(null);
  const [tailoringStarting, setTailoringStarting] = useState(false);
  const [tailoringStatus, setTailoringStatus] = useState<TailoringSessionStatusResponse | null>(null);
  const [tailoringResult, setTailoringResult] = useState<TailoringSessionResult | null>(null);
  const [promptCopied, setPromptCopied] = useState(false);
  const lastTailoringToast = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getLatestTailoringSession(applicationId).then((status) => {
      if (cancelled || !status) return;
      setTailoringStatus(status);
      setTailoringResult(status.result);
      // A status endpoint intentionally never returns the one-time code. A
      // placeholder session lets the application page retain draft review
      // actions after the user navigates away and comes back.
      setTailoringSession({
        protocol_version: 4,
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
      });
    }).catch(() => {
      // A new application normally has no tailoring session yet.
    });
    return () => { cancelled = true; };
  }, [applicationId]);

  useEffect(() => {
    if (!tailoringSession || isTerminalTailoringStatus(tailoringStatus?.status)) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const status = await getTailoringSessionStatus(tailoringSession.session_id);
        if (cancelled) return;
        setTailoringStatus(status);
        if (status.result) setTailoringResult(status.result);
        const toast = terminalTailoringToast(status.status);
        const toastKey = `${tailoringSession.session_id}:${status.status}`;
        if (toast && lastTailoringToast.current !== toastKey) {
          lastTailoringToast.current = toastKey;
          addToast(toast.message, toast.type);
        }
        if (status.status === "accepted") {
          await fetchApplication(tailoringSession.application_id);
        }
      } catch {
        // The shared API client reports actionable errors. Keep the last known
        // session state visible while the user can retry from this page.
      }
    };

    void poll();
    const timer = window.setInterval(() => { void poll(); }, 3000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [addToast, fetchApplication, tailoringSession, tailoringStatus?.status]);

  const startTailoring = useCallback(async () => {
    setTailoringStarting(true);
    try {
      const session = await createTailoringSession(applicationId);
      setTailoringSession(session);
      setTailoringStatus(null);
      setTailoringResult(null);
      setPromptCopied(false);
      addToast("Local tailoring session created", "info");
    } catch {
      addToast("Unable to create a local tailoring session", "error");
    } finally {
      setTailoringStarting(false);
    }
  }, [addToast, applicationId]);

  const copyPrompt = useCallback(async () => {
    if (!tailoringSession) return;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(tailoringSession.prompt);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = tailoringSession.prompt;
        textarea.setAttribute("readonly", "true");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }
      setPromptCopied(true);
      addToast("Prompt copied — paste it into your coding agent", "info");
    } catch {
      addToast("Unable to copy the tailoring prompt", "error");
    }
  }, [addToast, tailoringSession]);

  const cancelTailoring = useCallback(async () => {
    if (!tailoringSession) return;
    try {
      const status = await cancelTailoringSession(tailoringSession.session_id);
      setTailoringStatus(status);
      lastTailoringToast.current = `${tailoringSession.session_id}:cancelled`;
      addToast("Tailoring session cancelled", "info");
    } catch {
      addToast("Unable to cancel the tailoring session", "error");
    }
  }, [addToast, tailoringSession]);

  const acceptDraft = useCallback(async () => {
    if (!tailoringSession) return;
    try {
      await acceptTailoringDraft(tailoringSession.session_id);
      const currentStatus = await getTailoringSessionStatus(tailoringSession.session_id);
      setTailoringStatus(currentStatus);
      setTailoringResult(currentStatus.result);
      await fetchApplication(tailoringSession.application_id);
      addToast("Tailored CV accepted and linked to this application", "success");
    } catch {
      addToast("The tailored draft could not be accepted; the application may have changed", "error");
    }
  }, [addToast, fetchApplication, tailoringSession]);

  const rejectDraft = useCallback(async () => {
    if (!tailoringSession) return;
    try {
      await rejectTailoringDraft(tailoringSession.session_id);
      const currentStatus = await getTailoringSessionStatus(tailoringSession.session_id);
      setTailoringStatus(currentStatus);
      setTailoringResult(currentStatus.result);
      addToast("Tailored draft rejected", "info");
    } catch {
      addToast("Unable to reject the tailored draft", "error");
    }
  }, [addToast, tailoringSession]);

  return {
    tailoringSession,
    tailoringStarting,
    tailoringStatus,
    tailoringResult,
    promptCopied,
    startTailoring,
    copyPrompt,
    cancelTailoring,
    acceptDraft,
    rejectDraft,
  };
}
