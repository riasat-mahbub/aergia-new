import { useEffect, type ReactNode } from "react";
import ToastContainer from "@/components/common/Toast";
import { setApiErrorHandler } from "@/services/client";
import { useToastStore } from "@/store/uiStore";

interface ClientProvidersProps {
  children: ReactNode;
}

export default function ClientProviders({ children }: ClientProvidersProps) {
  useEffect(() => {
    const dispose = setApiErrorHandler((message) => {
      useToastStore.getState().addToast(message, "error");
    });
    return dispose;
  }, []);

  return (
    <>
      <ToastContainer />
      {children}
    </>
  );
}
