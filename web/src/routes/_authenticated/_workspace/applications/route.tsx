import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/_workspace/applications")({
  ssr: false,
  component: ApplicationsLayout,
});

function ApplicationsLayout() {
  return <Outlet />;
}
