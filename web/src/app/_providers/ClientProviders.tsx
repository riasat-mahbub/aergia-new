import { useEffect, type ReactNode } from "react";
import ToastContainer from "@/components/common/Toast";
import { setApiErrorHandler, setUnauthorizedHandler } from "@/services/client";
import { useToastStore } from "@/store/uiStore";
import { forgetAllKeys } from "@/store/llmKeyStore";

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
