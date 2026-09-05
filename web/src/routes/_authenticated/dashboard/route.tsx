import { createFileRoute, Outlet } from "@tanstack/react-router";
import { DashboardLayout } from "@/features/dashboard";

export const Route = createFileRoute("/_authenticated/dashboard")({
  ssr: "data-only",
  component: DashboardRouteLayout,
});

function DashboardRouteLayout() {
  return <DashboardLayout><Outlet /></DashboardLayout>;
}
