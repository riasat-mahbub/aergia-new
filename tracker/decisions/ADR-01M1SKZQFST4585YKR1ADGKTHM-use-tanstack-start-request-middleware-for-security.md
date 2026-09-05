---
SCHEMA: 4
FORMAT: project-tracker
ID: ADR-01M1SKZQFST4585YKR1ADGKTHM
TYPE: adr
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS:
- security
- tanstack-start
RELATIONS: null
AFFECTS:
  files:
  - web/src/middleware/security/contentSecurityPolicy.ts
  - web/src/middleware/security/nonce.ts
  - web/src/middleware/security/securityHeaders.ts
  - web/src/middleware/security/securityMiddleware.ts
  - web/src/middleware/security/types.ts
  - web/src/router.tsx
  - web/src/start.ts
  - web/vite.config.ts
  - web/server/api/[...path].ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-05T20:26:00.569242+00:00'
UPDATED_AT: '2026-09-05T20:26:00.569242+00:00'
---

# Use TanStack Start request middleware for security

## Background

Use TanStack Start request middleware as the application security boundary. Generate a fresh nonce per request, apply security headers from a dedicated web/src/middleware/security module, pass the nonce through Start request context into router SSR options, and register Start's CSRF middleware explicitly. Keep Nitro limited to the API gateway; deployment-specific forwarded-protocol trust remains out of scope until a public proxy is configured.

## Investigation

TanStack Start supports request middleware and its router SSR options accept a
nonce that is applied to generated document scripts. The application already
uses Nitro for the same-origin FastAPI API gateway, but no Nitro middleware is
needed for the security boundary. Keeping the policy in a dedicated frontend
middleware folder makes the boundary explicit and leaves proxy-specific HTTPS
trust out of the application until deployment is defined.


## Decision

Use a fresh 18-byte base64url nonce per request. Emit it in a production CSP
`script-src`, propagate it through Start request context, and configure
TanStack Router SSR with that nonce. Register Start's CSRF middleware explicitly
on the custom Start instance. Keep development-only Vite allowances out of the
production policy. Emit HSTS only when the request is natively HTTPS; do not
trust `X-Forwarded-Proto` yet.


## Implementation

`web/src/middleware/security/` owns nonce generation, CSP composition, security
headers, and the Start request middleware. `web/src/start.ts` registers the
security and CSRF middleware. `web/src/router.tsx` reads the request context and
passes the nonce to router SSR. Nitro remains responsible only for
`web/server/api/[...path].ts`.


## Verification

The typecheck, production build, architecture checks, codegen drift check, and
Ruff pass. A mock-API Start smoke confirmed security headers, matching SSR
nonces, and nonce rotation across requests.


## Follow-up

When deployment is designed, explicitly configure the trusted proxy chain and
decide whether HSTS should be enabled for the public origin. Add focused
middleware/auth tests as part of the replacement test suite.
