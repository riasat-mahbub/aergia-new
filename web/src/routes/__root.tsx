import {
  HeadContent,
  Outlet,
  Scripts,
  createRootRouteWithContext,
} from "@tanstack/react-router";
import { AuthStoreProvider, resolveSession } from "@/features/authentication";
import type { SessionResolveResponse } from "@/features/authentication";
import { LoadingPage, NotFoundPage as AppNotFoundPage, RootLayout } from "@/app-shell";
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
  pendingComponent: LoadingPage,
  notFoundComponent: AppNotFoundPage,
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
          <RootLayout>
            <Outlet />
          </RootLayout>
        </AuthStoreProvider>
        <Scripts />
      </body>
    </html>
  );
}
