import type { ReactNode } from "react";
import ErrorBoundary from "./ErrorPage";
import ClientProviders from "./ClientProviders";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-app-canvas">
      <ErrorBoundary>
        <ClientProviders>
          {children}
        </ClientProviders>
      </ErrorBoundary>
    </div>
  );
}
