import { createCsrfMiddleware, createStart } from "@tanstack/react-start";
import { securityMiddleware } from "./middleware/security/securityMiddleware";

const csrfMiddleware = createCsrfMiddleware({
  filter: ({ handlerType, request }) => handlerType === "serverFn" && request.method !== "GET",
});

export const startInstance = createStart(() => ({
  defaultSsr: true,
  requestMiddleware: [securityMiddleware, csrfMiddleware],
}));
