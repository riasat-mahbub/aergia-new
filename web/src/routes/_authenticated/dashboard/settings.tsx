import { createFileRoute } from "@tanstack/react-router";
import { SettingsPage } from "@/features/settings";

export const Route = createFileRoute("/_authenticated/dashboard/settings")({
  ssr: false,
  component: SettingsPage,
});
