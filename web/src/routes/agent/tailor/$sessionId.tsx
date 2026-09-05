import { createFileRoute } from "@tanstack/react-router";
import { TailoringSessionPage } from "@/features/tailoring";

export const Route = createFileRoute("/agent/tailor/$sessionId")({
  component: TailoringSessionRoute,
});

function TailoringSessionRoute() {
  const { sessionId } = Route.useParams();
  return <TailoringSessionPage sessionId={sessionId} />;
}
