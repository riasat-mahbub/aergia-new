import { createFileRoute } from "@tanstack/react-router";
import { LibraryPage } from "@/features/library";
import { z } from "zod";

export const Route = createFileRoute("/_authenticated/dashboard/library")({
  ssr: false,
  validateSearch: z.object({ kind: z.string().optional() }),
  component: LibraryRoute,
});

function LibraryRoute() {
  const { kind } = Route.useSearch();
  return <LibraryPage initialKind={kind} />;
}
