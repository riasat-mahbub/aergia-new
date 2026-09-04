import { Outlet } from "react-router-dom";
import ErrorBoundary from "./error";
import ClientProviders from "./providers/ClientProviders";

export default function RootLayout() {
  return (
    <div className="min-h-screen bg-app-canvas">
      <ErrorBoundary>
        <ClientProviders>
          <Outlet />
        </ClientProviders>
      </ErrorBoundary>
    </div>
  );
}
