import { useEffect, useRef } from "react";

interface TurnstileOptions {
  sitekey: string;
  action?: string;
  callback?: (token: string) => void;
  "expired-callback"?: () => void;
  "error-callback"?: () => void;
  "timeout-callback"?: () => void;
}

interface TurnstileApi {
  render: (container: HTMLElement, options: TurnstileOptions) => string;
  reset: (widgetId?: string) => void;
  remove: (widgetId?: string) => void;
}

declare global {
  interface Window {
    turnstile?: TurnstileApi;
  }
}

interface TurnstileWidgetProps {
  siteKey: string;
  action: string;
  resetKey: number;
  onToken: (token: string) => void;
  onError: () => void;
}

const SCRIPT_ID = "cloudflare-turnstile-script";
const SCRIPT_SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

function loadTurnstile(): Promise<TurnstileApi> {
  if (window.turnstile) return Promise.resolve(window.turnstile);

  return new Promise((resolve, reject) => {
    let script = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
    let intervalId: number | undefined;
    let timeoutId: number | undefined;

    const cleanup = () => {
      script?.removeEventListener("load", check);
      script?.removeEventListener("error", fail);
      if (intervalId !== undefined) window.clearInterval(intervalId);
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
    };
    const check = () => {
      if (window.turnstile) {
        cleanup();
        resolve(window.turnstile);
      }
    };
    const fail = () => {
      cleanup();
      reject(new Error("Turnstile script failed to load"));
    };

    if (!script) {
      script = document.createElement("script");
      script.id = SCRIPT_ID;
      script.src = SCRIPT_SRC;
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }
    script.addEventListener("load", check);
    script.addEventListener("error", fail);
    intervalId = window.setInterval(check, 50);
    timeoutId = window.setTimeout(fail, 10000);
    check();
  });
}

function TurnstileWidget({ siteKey, action, resetKey, onToken, onError }: TurnstileWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | undefined>(undefined);
  const resetKeyRef = useRef(resetKey);

  useEffect(() => {
    let disposed = false;
    const container = containerRef.current;
    if (!container) return undefined;

    void loadTurnstile()
      .then((turnstile) => {
        if (disposed || !container) return;
        widgetIdRef.current = turnstile.render(container, {
          sitekey: siteKey,
          action,
          callback: onToken,
          "expired-callback": () => onToken(""),
          "error-callback": onError,
          "timeout-callback": onError,
        });
        if (resetKeyRef.current > 0) turnstile.reset(widgetIdRef.current);
      })
      .catch(() => {
        if (!disposed) onError();
      });

    return () => {
      disposed = true;
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
      }
      widgetIdRef.current = undefined;
    };
  }, [action, onError, onToken, siteKey]);

  useEffect(() => {
    resetKeyRef.current = resetKey;
    if (resetKey > 0 && widgetIdRef.current && window.turnstile) {
      window.turnstile.reset(widgetIdRef.current);
    }
  }, [resetKey]);

  return <div ref={containerRef} aria-label="Security verification" />;
}

export default TurnstileWidget;
