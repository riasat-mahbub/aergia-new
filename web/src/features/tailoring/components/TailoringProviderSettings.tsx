import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Download, ExternalLink, Link2, ShieldCheck, Unplug } from "lucide-react";
import {
  completeTailoringProviderOAuthCallback,
} from "../api/providers";
import { useTailoringProviders } from "../hooks/useTailoringProviders";
import type {
  TailoringProvider,
  TailoringProviderOAuthCallbackRequest,
  TailoringProviderStatus,
} from "../types";

const useClientLayoutEffect = typeof window === "undefined" ? useEffect : useLayoutEffect;

type OAuthCallbackCapture =
  | { kind: "none" }
  | { kind: "invalid" }
  | { kind: "payload"; payload: TailoringProviderOAuthCallbackRequest };

function captureOAuthCallback(): OAuthCallbackCapture {
  const url = new URL(window.location.href);
  const parameterNames = ["code", "state", "error", "client_id"] as const;
  const hasCallbackParameter = parameterNames.some((name) => url.searchParams.has(name));
  if (!hasCallbackParameter) return { kind: "none" };

  const state = url.searchParams.get("state") ?? "";
  const code = url.searchParams.get("code") ?? "";
  const error = url.searchParams.get("error") ?? "";
  const clientId = url.searchParams.get("client_id") ?? "";
  parameterNames.forEach((name) => url.searchParams.delete(name));
  window.history.replaceState(
    window.history.state,
    "",
    `${url.pathname}${url.search}${url.hash}`,
  );

  if (!state.trim() || Boolean(code.trim()) === Boolean(error.trim())) return { kind: "invalid" };
  return {
    kind: "payload",
    payload: {
      state,
      ...(code ? { code } : {}),
      ...(error ? { error } : {}),
      ...(clientId ? { client_id: clientId } : {}),
    },
  };
}

function errorDetail(error: unknown, fallback: string): string {
  if (error && typeof error === "object" && "response" in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response;
    if (typeof response?.data?.detail === "string" && response.data.detail.trim()) return response.data.detail;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

function providerStatusLabel(status: TailoringProviderStatus): string {
  switch (status) {
    case "unavailable": return "Unavailable";
    case "disconnected": return "Not connected";
    case "setup_required": return "Setup required";
    case "ready": return "Connected and ready";
    case "reconnect": return "Reconnect required";
  }
}

function ProviderStatus({
  status,
  detail,
}: {
  status: TailoringProviderStatus | undefined;
  detail?: string | null;
}) {
  return (
    <div className="mt-3 border-t border-app-rule-soft pt-3" aria-live="polite">
      <p className="text-xs font-medium text-app-ink"><span className="font-normal text-app-ink-3">Status: </span>{status ? providerStatusLabel(status) : "Status not loaded"}</p>
      {detail && <p className="mt-1 break-words text-xs leading-5 text-app-ink-2">{detail}</p>}
    </div>
  );
}

export default function TailoringProviderSettings() {
  const { availability, refresh, connect, disconnect, checkGemini } = useTailoringProviders();
  const callbackRef = useRef<OAuthCallbackCapture | null>(null);
  const callbackCaptureAttemptedRef = useRef(false);
  const callbackHandledRef = useRef(false);
  const [callbackNotice, setCallbackNotice] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useClientLayoutEffect(() => {
    if (callbackCaptureAttemptedRef.current) return;
    callbackCaptureAttemptedRef.current = true;
    callbackRef.current = captureOAuthCallback();
    if (callbackRef.current.kind === "invalid") {
      setCallbackNotice("Provider sign-in could not be completed. Return to Settings and try again.");
    }
  }, []);

  useEffect(() => {
    const capture = callbackRef.current;
    if (callbackHandledRef.current || capture?.kind !== "payload") return;
    if (availability.state === "unsupported") {
      callbackHandledRef.current = true;
      callbackRef.current = null;
      return;
    }
    if (availability.state !== "loaded") return;

    callbackHandledRef.current = true;
    callbackRef.current = null;

    void completeTailoringProviderOAuthCallback(capture.payload).then(async (response) => {
      setCallbackNotice(response.detail || "Provider sign-in completed.");
      await refresh();
    }).catch((callbackError: unknown) => {
      setCallbackNotice(errorDetail(callbackError, "Provider sign-in could not be completed. Try connecting again."));
      void refresh();
    });
  }, [availability, refresh]);

  const performAction = async (key: string, action: () => Promise<unknown>, fallback: string) => {
    setBusyAction(key);
    setActionError(null);
    try {
      await action();
    } catch (error) {
      setActionError(errorDetail(error, fallback));
    } finally {
      setBusyAction(null);
    }
  };

  const providers = availability.state === "loaded" ? availability.providers : null;
  const isLoading = availability.state === "loading";
  const provider = (name: TailoringProvider) => providers?.[name];

  return (
    <section className="rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm" aria-labelledby="tailoring-provider-settings-heading" aria-busy={isLoading || busyAction !== null}>
      <div className="flex items-start gap-3">
        <div className="rounded-md bg-app-primary-soft p-2 text-app-primary"><Link2 className="h-5 w-5" /></div>
        <div>
          <h2 id="tailoring-provider-settings-heading" className="text-lg font-semibold text-app-ink">Optional AI providers</h2>
          {availability.state === "loaded" && <p className="mt-1 text-sm text-app-ink-2">Connect a provider to run tailoring there. Your profile and Library are used to prepare the tailored draft.</p>}
        </div>
      </div>

      {callbackNotice && <p className="mt-4 rounded-md bg-app-primary-soft px-3 py-2 text-xs leading-5 text-app-ink-2" role="status">{callbackNotice}</p>}
      {availability.state === "loading" && <p className="mt-4 text-sm text-app-ink-2" role="status">Checking provider availability…</p>}
      {availability.state === "unsupported" && <p className="mt-4 rounded-md bg-app-canvas px-3 py-2 text-sm text-app-ink-2" role="status">Optional provider connections are not available on this deployment. You can keep tailoring with your coding agent.</p>}
      {availability.state === "failed" && <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-md bg-app-danger-soft px-3 py-2 text-xs text-app-danger" role="alert"><span>{availability.message}</span><button type="button" onClick={() => void refresh()} className="font-medium underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary focus-visible:ring-offset-2">Retry</button></div>}
      {actionError && <p className="mt-4 text-xs leading-5 text-app-danger" role="alert">{actionError}</p>}

      {availability.state === "loaded" && <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <section className="min-w-0" aria-labelledby="chatgpt-provider-heading">
          <h3 id="chatgpt-provider-heading" className="text-sm font-semibold text-app-ink">ChatGPT</h3>
          <p className="mt-1 text-xs leading-5 text-app-ink-2">Sign in to connect your ChatGPT account for optional tailoring runs.</p>
          <ProviderStatus status={provider("chatgpt")?.status} detail={provider("chatgpt")?.detail} />
          <div className="mt-3 flex flex-wrap gap-2">
            {provider("chatgpt")?.status === "ready" ? (
              <button type="button" onClick={() => void performAction("disconnect-chatgpt", async () => { await disconnect("chatgpt"); await refresh(); }, "Unable to disconnect ChatGPT.")} disabled={busyAction !== null || isLoading} className="inline-flex items-center gap-1 rounded-md border border-app-rule-strong px-3 py-2 text-xs font-medium text-app-ink-2 hover:bg-app-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary focus-visible:ring-offset-2 disabled:opacity-50">
                <Unplug className="h-3.5 w-3.5" />{busyAction === "disconnect-chatgpt" ? "Disconnecting…" : "Disconnect"}
              </button>
            ) : provider("chatgpt") && provider("chatgpt")?.status !== "unavailable" ? (
              <button type="button" onClick={() => void performAction("connect-chatgpt", () => connect("chatgpt"), "Unable to connect ChatGPT.")} disabled={busyAction !== null || isLoading} className="inline-flex items-center gap-1 rounded-md bg-app-primary px-3 py-2 text-xs font-medium text-white hover:bg-app-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary focus-visible:ring-offset-2 disabled:opacity-50">
                <ExternalLink className="h-3.5 w-3.5" />{busyAction === "connect-chatgpt" ? "Opening sign-in…" : provider("chatgpt")?.status === "reconnect" ? "Reconnect ChatGPT" : "Connect ChatGPT"}
              </button>
            ) : null}
          </div>
        </section>

        <section className="min-w-0" aria-labelledby="gemini-provider-heading">
          <h3 id="gemini-provider-heading" className="text-sm font-semibold text-app-ink">Gemini</h3>
          <p className="mt-1 text-xs leading-5 text-app-ink-2">Connect Google, then set up Gemini Tasks to run a tailoring task.</p>
          <ProviderStatus status={provider("gemini")?.status} detail={provider("gemini")?.detail} />
          <div className="mt-3 flex flex-wrap gap-2">
            {provider("gemini")?.status === "ready" ? (
              <button type="button" onClick={() => void performAction("disconnect-gemini", async () => { await disconnect("gemini"); await refresh(); }, "Unable to disconnect Gemini.")} disabled={busyAction !== null || isLoading} className="inline-flex items-center gap-1 rounded-md border border-app-rule-strong px-3 py-2 text-xs font-medium text-app-ink-2 hover:bg-app-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary focus-visible:ring-offset-2 disabled:opacity-50">
                <Unplug className="h-3.5 w-3.5" />{busyAction === "disconnect-gemini" ? "Disconnecting…" : "Disconnect"}
              </button>
            ) : provider("gemini")?.status === "disconnected" || provider("gemini")?.status === "reconnect" ? (
              <button type="button" onClick={() => void performAction("connect-gemini", () => connect("gemini"), "Unable to connect Gemini.")} disabled={busyAction !== null || isLoading} className="inline-flex items-center gap-1 rounded-md bg-app-primary px-3 py-2 text-xs font-medium text-white hover:bg-app-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary focus-visible:ring-offset-2 disabled:opacity-50">
                <ExternalLink className="h-3.5 w-3.5" />{busyAction === "connect-gemini" ? "Opening sign-in…" : provider("gemini")?.status === "reconnect" ? "Reconnect Gemini" : "Connect Gemini"}
              </button>
            ) : null}
            {(provider("gemini")?.status === "ready" || provider("gemini")?.status === "setup_required") && (
              <button type="button" onClick={() => void performAction("check-gemini", async () => { await checkGemini(); await refresh(); }, "Unable to check Gemini Tasks setup.")} disabled={busyAction !== null || isLoading} className="inline-flex items-center gap-1 rounded-md border border-app-primary-soft px-3 py-2 text-xs font-medium text-app-primary hover:bg-app-primary-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary focus-visible:ring-offset-2 disabled:opacity-50">
                <ShieldCheck className="h-3.5 w-3.5" />{busyAction === "check-gemini" ? "Checking setup…" : "Check Gemini setup"}
              </button>
            )}
          </div>

          {provider("gemini")?.status === "setup_required" && (
            <div className="mt-4 border-t border-app-rule-soft pt-3" aria-labelledby="gemini-setup-heading">
              <h4 id="gemini-setup-heading" className="text-xs font-semibold text-app-ink">Gemini setup in Canada</h4>
              <ol className="mt-2 list-decimal space-y-1 pl-4 text-xs leading-5 text-app-ink-2">
                <li><a href="/api/v1/tailoring/providers/skill.zip" download className="inline-flex items-center gap-1 font-medium text-app-primary hover:underline">Download the Aergia skill <Download className="h-3 w-3" /></a>, then import it in Gemini.</li>
                <li>In Gemini Tasks, create a Gmail monitor for the exact subject prefix <code className="rounded bg-app-surface px-1">[Aergia Tailoring]</code>.</li>
                <li>Select the Aergia skill for the task, then return here and check the setup.</li>
              </ol>
              <p className="mt-2 text-xs leading-5 text-app-ink-3">Gemini Tasks availability can vary by account and region. If Tasks are unavailable for your account in Canada, Gemini tailoring will remain disabled.</p>
            </div>
          )}
        </section>
      </div>
      }

      {availability.state === "loaded" && (
        <div className="mt-4 flex gap-2 rounded-md bg-app-primary-soft px-3 py-3 text-xs text-app-ink-2">
          <ShieldCheck className="h-4 w-4 shrink-0 text-app-primary" />
          <p>Provider tailoring is optional. You can keep using the default coding-agent flow, and every provider-created draft still needs your review before it can change the linked CV.</p>
        </div>
      )}
      <p className="sr-only" role="status" aria-live="polite">{isLoading ? "Loading provider status" : availability.state === "loaded" ? "Provider status loaded" : availability.state === "unsupported" ? "Provider status unavailable on this deployment" : "Provider status could not be loaded"}</p>
    </section>
  );
}
