import { createFileRoute } from "@tanstack/react-router";
import DashboardLayout from "@/app/dashboard/layout";

export const Route = createFileRoute("/_authenticated/dashboard")({
  ssr: "data-only",
  component: DashboardLayout,
});
