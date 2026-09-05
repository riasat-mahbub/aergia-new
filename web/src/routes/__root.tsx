import {
  HeadContent,
  Scripts,
  createRootRouteWithContext,
} from "@tanstack/react-router";
import type { SessionResolveResponse } from "@/contracts/auth";
import { resolveSession } from "@/services/session.functions";
import RootLayout from "@/app/layout";
import Loading from "@/app/loading";
import NotFoundPage from "@/app/not-found";
import { AuthStoreProvider } from "@/store/authStore";
import "@/index.css";
import "react-day-picker/style.css";

export interface StartRouterContext {
  auth: SessionResolveResponse;
}

export const Route = createRootRouteWithContext<StartRouterContext>()({
  beforeLoad: async () => ({ auth: await resolveSession() }),
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Aergia CV Builder" },
    ],
  }),
  pendingComponent: Loading,
  notFoundComponent: NotFoundPage,
  component: RootDocument,
});

function RootDocument() {
  const { auth } = Route.useRouteContext();
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        <AuthStoreProvider initialSession={auth}>
          <RootLayout />
        </AuthStoreProvider>
        <Scripts />
      </body>
    </html>
  );
}
