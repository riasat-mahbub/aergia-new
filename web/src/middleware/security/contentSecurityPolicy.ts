export interface ContentSecurityPolicyOptions {
  nonce: string;
  production: boolean;
}

/**
 * Keep the policy in one place so Start document responses and future runtime
 * adapters do not drift from one another.
 */
export function buildContentSecurityPolicy({ nonce, production }: ContentSecurityPolicyOptions): string {
  const developmentSources = production
    ? []
    : ["http://localhost:5173"];
  const developmentConnectSources = production
    ? []
    : ["http://localhost:5173", "ws://localhost:5173"];

  const defaultSources = ["'self'", ...developmentSources];
  const connectSources = ["'self'", ...developmentConnectSources, "https://challenges.cloudflare.com"];
  const scriptSources = [
    "'self'",
    `'nonce-${nonce}'`,
    ...(production ? [] : ["'unsafe-inline'", "'unsafe-eval'"]),
    "https://challenges.cloudflare.com",
  ];

  return [
    `default-src ${defaultSources.join(" ")}`,
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    `script-src ${scriptSources.join(" ")}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src ${connectSources.join(" ")}`,
    "frame-src 'self' https://challenges.cloudflare.com",
  ].join("; ");
}
