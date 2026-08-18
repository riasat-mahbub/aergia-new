import { type ReactNode } from "react";
import { Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../../lib/store/authStore";
import { FileText, Settings, LogOut, Library, BriefcaseBusiness, LayoutDashboard } from "lucide-react";

interface AppLayoutProps {
  children: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const isBuilder = location.pathname.includes("/builder/");

  const navItems = [
    { to: "/dashboard", label: "Dashboard", Icon: LayoutDashboard, end: true },
    { to: "/dashboard/cvs", label: "CVs", Icon: FileText },
    { to: "/dashboard/library", label: "Library", Icon: Library },
    { to: "/dashboard/applications", label: "Applications", Icon: BriefcaseBusiness },
  ];

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-app-canvas">
      <nav className="flex min-h-14 flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b bg-app-surface px-4 py-2 shadow-sm sm:px-6 sm:py-0">
        <div className="flex min-w-0 flex-1 items-center gap-4">
          {isBuilder ? (
            <Link
              to="/dashboard/cvs"
              className="flex items-center gap-1.5 text-sm font-medium text-app-ink-2 hover:text-app-ink"
            >
              <FileText className="h-4 w-4" />
              Back to CVs
            </Link>
          ) : (
            <Link to="/dashboard" className="text-lg font-bold text-app-ink">
              Aergia
            </Link>
          )}
          {!isBuilder && (
            <div className="flex min-w-0 items-center gap-1 overflow-x-auto py-1">
              {navItems.map(({ to, label, Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) => `flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm transition ${
                    isActive
                      ? "bg-app-primary-soft font-medium text-app-primary"
                      : "text-app-ink-3 hover:bg-app-surface-muted hover:text-app-ink-2"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </NavLink>
              ))}
            </div>
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
