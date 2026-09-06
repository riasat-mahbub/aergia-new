import { createFileRoute } from "@tanstack/react-router";
import { CvListPage } from "@/features/cvs";

export const Route = createFileRoute("/_authenticated/_workspace/cvs")({
  ssr: false,
  component: CvListPage,
});
