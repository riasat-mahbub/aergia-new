import { createFileRoute } from "@tanstack/react-router";
import DashboardPage from "@/app/dashboard/page";

export const Route = createFileRoute("/_authenticated/dashboard/")({
  ssr: false,
  component: DashboardPage,
});
