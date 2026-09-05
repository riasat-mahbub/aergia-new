import { createMiddleware } from "@tanstack/react-start";
import { getRequestProtocol, setResponseHeader } from "@tanstack/react-start/server";
import { createCspNonce } from "./nonce";
import { buildSecurityHeaders } from "./securityHeaders";

function isSecureRequest(): boolean {
  // Forwarded-protocol trust is deployment-specific and remains disabled
  // until the public proxy is configured explicitly.
  return getRequestProtocol({ xForwardedProto: false }) === "https";
}

export const securityMiddleware = createMiddleware({ type: "request" }).server(
  ({ next }) => {
    const cspNonce = createCspNonce();
    const headers = buildSecurityHeaders({
      nonce: cspNonce,
      production: process.env.NODE_ENV === "production",
      secureRequest: isSecureRequest(),
    });

    setResponseHeader("content-security-policy", headers["content-security-policy"]);
    setResponseHeader("x-content-type-options", headers["x-content-type-options"]);
    setResponseHeader("x-frame-options", headers["x-frame-options"]);
    setResponseHeader("referrer-policy", headers["referrer-policy"]);
    setResponseHeader("permissions-policy", headers["permissions-policy"]);
    if (headers["strict-transport-security"]) {
      setResponseHeader("strict-transport-security", headers["strict-transport-security"]);
    }
    return next({ context: { cspNonce } });
  },
);
