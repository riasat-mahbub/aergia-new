import { buildContentSecurityPolicy } from "./contentSecurityPolicy";

export interface SecurityHeaderOptions {
  nonce: string;
  production: boolean;
  secureRequest: boolean;
}

export function buildSecurityHeaders({ nonce, production, secureRequest }: SecurityHeaderOptions) {
  return {
    "content-security-policy": buildContentSecurityPolicy({ nonce, production }),
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    ...(production && secureRequest
      ? { "strict-transport-security": "max-age=31536000; includeSubDomains" }
      : {}),
  };
}
