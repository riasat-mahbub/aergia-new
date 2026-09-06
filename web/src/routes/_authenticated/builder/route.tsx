import { createFileRoute, Outlet } from "@tanstack/react-router";
import { WorkspaceLayout } from "@/app-shell";

export const Route = createFileRoute("/_authenticated/builder")({
  ssr: "data-only",
  component: BuilderLayout,
});

function BuilderLayout() {
  return <WorkspaceLayout showNavbar={false}><Outlet /></WorkspaceLayout>;
}
