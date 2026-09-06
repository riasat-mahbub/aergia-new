import { Link, useNavigate, useRouter } from "@tanstack/react-router";
import { BriefcaseBusiness, FileText, LayoutDashboard, Library, LogOut, Settings } from "lucide-react";
import { useAuthStore } from "@/features/authentication";

const navItems = [
  { to: "/dashboard", label: "Dashboard", Icon: LayoutDashboard, end: true },
  { to: "/dashboard/cvs", label: "CVs", Icon: FileText },
  { to: "/dashboard/library", label: "Library", Icon: Library },
  { to: "/dashboard/applications", label: "Applications", Icon: BriefcaseBusiness },
  { to: "/dashboard/settings", label: "Settings", Icon: Settings },
];

export default function SiteNavbar() {
  const navigate = useNavigate();
  const router = useRouter();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = async () => {
    await logout();
    await router.invalidate({ sync: true });
    navigate({ to: "/login" });
  };

  return (
    <header className="flex min-h-14 flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b bg-app-surface px-4 py-2 shadow-sm sm:px-6 sm:py-0">
      <div className="flex min-w-0 flex-1 items-center gap-4">
        <Link to="/" className="shrink-0 text-lg font-bold text-app-ink">
          Aergia
        </Link>
        {isAuthenticated && (
          <nav aria-label="Primary" className="flex min-w-0 items-center gap-1 overflow-x-auto py-1">
            {navItems.map(({ to, label, Icon, end }) => (
              <Link
                key={to}
                to={to}
                activeOptions={{ exact: end }}
                activeProps={{ className: "flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm transition bg-app-primary-soft font-medium text-app-primary" }}
                inactiveProps={{ className: "flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm transition text-app-ink-3 hover:bg-app-surface-muted hover:text-app-ink-2" }}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            ))}
          </nav>
        )}
      </div>
      <div className="flex items-center gap-3">
        {isAuthenticated ? (
          <button
            type="button"
            onClick={handleLogout}
            className="rounded p-1.5 text-app-ink-3 hover:text-app-ink"
            title="Logout"
            aria-label="Log out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        ) : (
          <Link
            to="/login"
            className="rounded-md border border-app-primary-soft px-4 py-2 text-sm text-app-primary hover:bg-app-primary-soft"
          >
            Sign in
          </Link>
        )}
      </div>
    </header>
  );
}
