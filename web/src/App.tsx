import { Outlet } from "react-router-dom";
import ToastContainer from "./components/common/Toast";
import ErrorBoundary from "./components/common/ErrorBoundary";

export default function App() {
  return (
    <div className="min-h-screen bg-app-canvas">
      <ErrorBoundary>
      <ToastContainer />
      <Outlet />
      </ErrorBoundary>
    </div>
  );
}
