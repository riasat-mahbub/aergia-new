import { type ReactNode } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../../lib/store/authStore";
import { FileText, Settings, LogOut, Library, BriefcaseBusiness } from "lucide-react";

interface AppLayoutProps {
  children: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const isBuilder = location.pathname.includes("/builder/");

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-app-canvas">
      <nav className="flex h-14 items-center justify-between border-b bg-app-surface px-6 shadow-sm">
        <div className="flex items-center gap-6">
          {isBuilder ? (
            <Link
              to="/dashboard"
              className="flex items-center gap-1.5 text-sm font-medium text-app-ink-2 hover:text-app-ink"
            >
              <FileText className="h-4 w-4" />
              My CVs
            </Link>
          ) : (
            <Link to="/" className="text-lg font-bold text-app-ink">
              Aergia
            </Link>
          )}
          {!isBuilder && (
            <Link
              to="/dashboard"
              className="flex items-center gap-1.5 text-sm text-app-ink-3 hover:text-app-ink-2"
            >
              <FileText className="h-4 w-4" />
              My CVs
            </Link>
          )}
          {!isBuilder && (
            <Link
              to="/dashboard/library"
              className="flex items-center gap-1.5 text-sm text-app-ink-3 hover:text-app-ink-2"
            >
              <Library className="h-4 w-4" />
              Library
            </Link>
          )}
          {!isBuilder && (
            <Link
              to="/dashboard/applications"
              className="flex items-center gap-1.5 text-sm text-app-ink-3 hover:text-app-ink-2"
            >
              <BriefcaseBusiness className="h-4 w-4" />
              Applications
            </Link>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/dashboard/settings"
            className="rounded p-1.5 text-app-ink-3 hover:text-app-ink"
            title="Settings"
          >
            <Settings className="h-4 w-4" />
          </Link>
          <button
            onClick={handleLogout}
            className="rounded p-1.5 text-app-ink-3 hover:text-app-ink"
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
