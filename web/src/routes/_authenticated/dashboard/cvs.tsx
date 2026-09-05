import { createFileRoute } from "@tanstack/react-router";
import CvsPage from "@/app/dashboard/cvs/page";

export const Route = createFileRoute("/_authenticated/dashboard/cvs")({
  ssr: false,
  component: CvsPage,
});
