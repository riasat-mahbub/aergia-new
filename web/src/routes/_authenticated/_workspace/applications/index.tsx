import { createFileRoute } from "@tanstack/react-router";
import { ApplicationListPage } from "@/features/applications";

export const Route = createFileRoute("/_authenticated/_workspace/applications/")({
  ssr: false,
  component: ApplicationListPage,
});
