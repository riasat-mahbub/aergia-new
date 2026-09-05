import { createFileRoute } from "@tanstack/react-router";
import ApplicationsPage from "@/app/dashboard/applications/page";

export const Route = createFileRoute("/_authenticated/dashboard/applications")({
  ssr: false,
  component: ApplicationsPage,
});
