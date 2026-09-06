import type { ReactNode } from "react";
import { SiteNavbar } from "@/features/app-shell";

interface DashboardLayoutProps {
  children: ReactNode;
  showNavbar?: boolean;
}

export default function DashboardLayout({ children, showNavbar = true }: DashboardLayoutProps) {

  return (
    <div className="min-h-screen bg-app-canvas">
      {showNavbar && <SiteNavbar />}
      <main>{children}</main>
    </div>
  );
}
