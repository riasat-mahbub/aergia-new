import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/builder/")({
  beforeLoad: () => {
    throw redirect({ to: "/cvs" });
  },
});
