import { Outlet } from "react-router-dom";
import { useEffect } from "react";
import { useAuthStore } from "./lib/store/authStore";
import ToastContainer from "./components/common/Toast";
import ErrorBoundary from "./components/common/ErrorBoundary";

export default function App() {
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  return (
    <div className="min-h-screen bg-gray-50">
      <ErrorBoundary>
      <ToastContainer />
      <Outlet />
      </ErrorBoundary>
    </div>
  );
}
