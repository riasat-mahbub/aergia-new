import { Outlet } from "@/lib/routerCompat";
import ErrorBoundary from "./error";
import ClientProviders from "./_providers/ClientProviders";

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
