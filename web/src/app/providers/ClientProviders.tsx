import type { ReactNode } from "react";
import ToastContainer from "@/components/common/Toast";

interface ClientProvidersProps {
  children: ReactNode;
}

export default function ClientProviders({ children }: ClientProvidersProps) {
  return (
    <>
      <ToastContainer />
      {children}
    </>
  );
}
