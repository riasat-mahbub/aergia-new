import type { ReactNode } from "react";
import ErrorBoundary from "../fallbacks/ErrorPage";
import ClientProviders from "../providers/ClientProviders";

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
