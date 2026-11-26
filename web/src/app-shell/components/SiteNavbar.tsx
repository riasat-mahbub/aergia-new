import { Link, useNavigate, useRouter } from "@tanstack/react-router";
import { BriefcaseBusiness, FileText, LayoutDashboard, Library, LogOut, Menu, Settings, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { useAuthStore } from "@/features/authentication";

const navItems = [
  { to: "/dashboard", label: "Dashboard", Icon: LayoutDashboard, end: true },
  { to: "/cvs", label: "CVs", Icon: FileText },
  { to: "/library", label: "Library", Icon: Library },
  { to: "/applications", label: "Applications", Icon: BriefcaseBusiness },
  { to: "/settings", label: "Settings", Icon: Settings },
];

const navigationId = "workspace-primary-navigation";

export default function SiteNavbar() {
  const navigate = useNavigate();
  const router = useRouter();
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const [isMobileNavigationOpen, setIsMobileNavigationOpen] = useState(false);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const logout = useAuthStore((state) => state.logout);

  useEffect(() => {
    return router.subscribe("onBeforeNavigate", () => {
      setIsMobileNavigationOpen(false);
    });
  }, [router]);

  const closeMobileNavigation = (restoreFocus = false) => {
    setIsMobileNavigationOpen(false);
    if (restoreFocus) menuButtonRef.current?.focus();
  };

  const handleHeaderKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape" && isMobileNavigationOpen) {
      event.preventDefault();
      closeMobileNavigation(true);
    }
  };

  const handleNavigationLinkClick = () => {
    if (isMobileNavigationOpen) closeMobileNavigation(true);
  };

  const handleLogout = async () => {
    await logout();
    await router.invalidate({ sync: true });
    navigate({ to: "/login" });
  };

  return (
    <header
      onKeyDown={handleHeaderKeyDown}
      className="flex min-h-14 flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b bg-app-surface px-4 py-2 shadow-sm sm:px-6 sm:py-0"
    >
      <Link to="/" className="shrink-0 text-lg font-bold text-app-ink">
        Aergia
      </Link>
      {isAuthenticated && (
        <button
          ref={menuButtonRef}
          type="button"
          aria-expanded={isMobileNavigationOpen}
          aria-controls={navigationId}
          onClick={() => setIsMobileNavigationOpen((isOpen) => !isOpen)}
          className="order-2 ml-auto inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-md border border-app-rule-strong bg-app-surface px-3 text-sm font-medium text-app-ink-2 transition-colors hover:bg-app-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary focus-visible:ring-offset-2 md:hidden"
        >
          {isMobileNavigationOpen ? (
            <X aria-hidden="true" className="h-4 w-4" />
          ) : (
            <Menu aria-hidden="true" className="h-4 w-4" />
          )}
          Menu
        </button>
      )}
      {isAuthenticated && (
        <nav
          id={navigationId}
          aria-label="Primary"
          className={`order-3 w-full flex-col gap-1 border-t border-app-rule py-2 md:order-2 md:w-auto md:flex-row md:items-center md:border-0 md:py-0 ${isMobileNavigationOpen ? "flex" : "hidden md:flex"}`}
        >
          {navItems.map(({ to, label, Icon, end }) => (
            <Link
              key={to}
              to={to}
              activeOptions={{ exact: end }}
              onClick={handleNavigationLinkClick}
              className="flex min-h-11 w-full items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors md:min-h-0 md:w-auto md:gap-1.5 md:px-2.5 md:py-1.5"
              activeProps={{
                className:
                  "bg-app-primary-soft font-medium text-app-primary",
              }}
              inactiveProps={{
                className:
                  "text-app-ink-3 hover:bg-app-surface-muted hover:text-app-ink-2",
              }}
            >
              <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          ))}
        </nav>
      )}
      {isAuthenticated ? (
        <button
          type="button"
          onClick={handleLogout}
          className="order-2 inline-flex h-11 w-11 items-center justify-center rounded-md text-app-ink-3 transition-colors hover:bg-app-surface-muted hover:text-app-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary focus-visible:ring-offset-2 md:order-3 md:ml-auto"
          title="Log out"
          aria-label="Log out"
        >
          <LogOut aria-hidden="true" className="h-4 w-4" />
        </button>
      ) : (
        <Link
          to="/login"
          className="order-2 ml-auto rounded-md border border-app-primary-soft px-4 py-2 text-sm text-app-primary hover:bg-app-primary-soft"
        >
          Sign in
        </Link>
      )}
    </header>
  );
}
