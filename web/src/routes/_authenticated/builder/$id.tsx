import { createFileRoute } from "@tanstack/react-router";
import { BuilderPage } from "@/features/builder";
import { z } from "zod";

export const Route = createFileRoute("/_authenticated/builder/$id")({
  ssr: "data-only",
  validateSearch: z.object({ application: z.string().optional() }),
  component: BuilderRoute,
});

function BuilderRoute() {
  const { id } = Route.useParams();
  const { application } = Route.useSearch();
  return <BuilderPage cvId={id} applicationId={application ?? null} />;
}
