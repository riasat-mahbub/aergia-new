import { createFileRoute } from "@tanstack/react-router";
import SettingsPage from "@/app/dashboard/settings/page";

export const Route = createFileRoute("/_authenticated/dashboard/settings")({
  ssr: false,
  component: SettingsPage,
});
