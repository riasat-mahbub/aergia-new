import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated")({
  beforeLoad: ({ context }) => {
    if (!context.auth.authenticated) {
      throw redirect({ to: "/login" });
    }
    return { auth: context.auth };
  },
});
