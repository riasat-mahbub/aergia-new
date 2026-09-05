import { createFileRoute } from "@tanstack/react-router";
import ApplicationDetailPage from "@/app/dashboard/applications/[id]/page";

export const Route = createFileRoute("/_authenticated/dashboard/applications/$id")({
  ssr: false,
  component: ApplicationDetailPage,
});
