import { createFileRoute } from "@tanstack/react-router";
import { RegisterPage } from "@/features/authentication";

export const Route = createFileRoute("/register")({
  component: RegisterPage,
});
