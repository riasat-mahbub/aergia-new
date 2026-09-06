import type { ReactNode } from "react";
import SiteNavbar from "./components/SiteNavbar";

interface WorkspaceLayoutProps {
  children: ReactNode;
  showNavbar?: boolean;
}

export default function WorkspaceLayout({ children, showNavbar = true }: WorkspaceLayoutProps) {

  return (
    <div className="min-h-screen bg-app-canvas">
      {showNavbar && <SiteNavbar />}
      <main>{children}</main>
    </div>
  );
}
