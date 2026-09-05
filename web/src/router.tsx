import { getGlobalStartContext } from "@tanstack/react-start";
import { createRouter } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";
import type { StartRequestContext } from "./middleware/security/types";

export function getRouter() {
  const requestContext = getGlobalStartContext();

  return createRouter({
    routeTree,
    context: {
      auth: undefined!,
    },
    ssr: requestContext?.cspNonce ? { nonce: requestContext.cspNonce } : undefined,
    scrollRestoration: true,
    defaultPreload: "intent",
  });
}

declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof getRouter>;
    server: { requestContext: StartRequestContext };
  }
}
