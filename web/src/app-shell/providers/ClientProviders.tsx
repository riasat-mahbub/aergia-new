import { useEffect, type ReactNode } from "react";
import ToastContainer from "@/shared/ui/Toast";
import { setApiErrorHandler, setUnauthorizedHandler } from "@/shared/api/client";
import { useToastStore } from "@/shared/state/uiStore";
import { forgetAllKeys } from "@/features/llm-credentials";

interface ClientProvidersProps {
  children: ReactNode;
}

export default function ClientProviders({ children }: ClientProvidersProps) {
  useEffect(() => {
    const disposeError = setApiErrorHandler((message) => {
      useToastStore.getState().addToast(message, "error");
    });
    const disposeUnauthorized = setUnauthorizedHandler(() => {
      forgetAllKeys();
      if (typeof localStorage !== "undefined") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      }
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    });
    return () => {
      disposeError();
      disposeUnauthorized();
    };
  }, []);

  return (
    <>
      <ToastContainer />
      {children}
    </>
  );
}
