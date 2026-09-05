import { createFileRoute } from "@tanstack/react-router";
import DashboardLayout from "@/app/dashboard/layout";

export const Route = createFileRoute("/_authenticated/builder")({
  ssr: "data-only",
  component: DashboardLayout,
});
