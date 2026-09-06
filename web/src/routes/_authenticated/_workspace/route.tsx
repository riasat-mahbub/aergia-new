import { createFileRoute, Outlet } from "@tanstack/react-router";
import { WorkspaceLayout } from "@/app-shell";

export const Route = createFileRoute("/_authenticated/_workspace")({
  ssr: "data-only",
  component: WorkspaceRouteLayout,
});

function WorkspaceRouteLayout() {
  return <WorkspaceLayout><Outlet /></WorkspaceLayout>;
}
