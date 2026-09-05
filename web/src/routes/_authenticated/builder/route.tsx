import { createFileRoute, Outlet } from "@tanstack/react-router";
import { DashboardLayout } from "@/features/dashboard";

export const Route = createFileRoute("/_authenticated/builder")({
  ssr: "data-only",
  component: BuilderLayout,
});

function BuilderLayout() {
  return <DashboardLayout><Outlet /></DashboardLayout>;
}
