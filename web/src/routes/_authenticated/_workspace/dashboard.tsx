import { createFileRoute } from "@tanstack/react-router";
import { DashboardPage } from "@/features/dashboard";

export const Route = createFileRoute("/_authenticated/_workspace/dashboard")({
  ssr: false,
  component: DashboardPage,
});
