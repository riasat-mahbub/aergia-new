import { createFileRoute } from "@tanstack/react-router";
import BuilderPage from "@/app/builder/[id]/page";
import { z } from "zod";

export const Route = createFileRoute("/_authenticated/builder/$id")({
  ssr: "data-only",
  validateSearch: z.object({ application: z.string().optional() }),
  component: BuilderPage,
});
