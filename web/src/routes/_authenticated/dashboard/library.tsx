import { createFileRoute } from "@tanstack/react-router";
import LibraryPage from "@/app/dashboard/library/page";
import { z } from "zod";

export const Route = createFileRoute("/_authenticated/dashboard/library")({
  ssr: false,
  validateSearch: z.object({ kind: z.string().optional() }),
  component: LibraryPage,
});
