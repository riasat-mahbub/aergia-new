import { createFileRoute } from "@tanstack/react-router";
import { ApplicationDetailPage } from "@/features/applications";

export const Route = createFileRoute("/_authenticated/dashboard/applications/$id")({
  ssr: false,
  component: ApplicationDetailRoute,
});

function ApplicationDetailRoute() {
  const { id } = Route.useParams();
  return <ApplicationDetailPage applicationId={id} />;
}
