import { createFileRoute } from "@tanstack/react-router";
import TailorPage from "@/app/agent/tailor/[sessionId]/page";

export const Route = createFileRoute("/agent/tailor/$sessionId")({
  component: TailorPage,
});
