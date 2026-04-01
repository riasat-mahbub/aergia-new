import { type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../lib/store/authStore";
import { FileText, Settings, LogOut } from "lucide-react";

interface AppLayoutProps {
  children: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="flex h-14 items-center justify-between border-b bg-white px-6 shadow-sm">
        <div className="flex items-center gap-6">
          <Link to="/dashboard" className="text-lg font-bold text-gray-900">
            Aergia
          </Link>
          <Link
            to="/dashboard"
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
          >
            <FileText className="h-4 w-4" />
            My CVs
          </Link>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/dashboard/settings"
            className="rounded p-1.5 text-gray-400 hover:text-gray-600"
            title="Settings"
          >
            <Settings className="h-4 w-4" />
          </Link>
          <button
            onClick={handleLogout}
            className="rounded p-1.5 text-gray-400 hover:text-gray-600"
            title="Logout"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </nav>
      <main>{children}</main>
    </div>
  );
}
