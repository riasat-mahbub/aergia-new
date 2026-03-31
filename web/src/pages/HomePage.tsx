import { Navigate, useNavigate } from "react-router-dom";
import { useAuthStore } from "../lib/store/authStore";

export default function HomePage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
      <h1 className="text-5xl font-bold text-gray-900">Aergia</h1>
      <p className="mt-3 text-lg text-gray-600">Build beautiful CVs in minutes</p>
      <div className="mt-8 flex gap-4">
        <button
          onClick={() => navigate("/login")}
          className="rounded-md bg-blue-600 px-6 py-2 text-sm text-white hover:bg-blue-700"
        >
          Sign in
        </button>
        <button
          onClick={() => navigate("/register")}
          className="rounded-md border border-gray-300 bg-white px-6 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          Get started
        </button>
      </div>
    </div>
  );
}
