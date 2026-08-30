---
SCHEMA: 4
FORMAT: project-tracker
ID: ADR-01M17ZKK02PDCJE0S199HDRVBA
TYPE: adr
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- security
- rate-limiting
- operations
RELATIONS: null
AFFECTS: null
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-30T00:02:45.890554+00:00'
UPDATED_AT: '2026-08-30T00:02:45.890554+00:00'
---

# Rate limiting for the supported single-process deployment

## Background

The API is currently launched as one Uvicorn process by `dev.sh` and
`docker-compose.yml`. SlowAPI is present and decorated routes have limits, but
the application did not install `SlowAPIMiddleware`, so its configured
`default_limits` were not applied to undecorated routes.

## Investigation

The installed SlowAPI behavior was verified directly: `default_limits` are
checked by `SlowAPIMiddleware`; route decorators are checked independently.
Before the middleware was installed, an undecorated endpoint was not covered
by the default limit. After installation, the same endpoint returned `429`
on request 101 and emitted `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
`X-RateLimit-Reset`, and `Retry-After` headers.

The supported deployment is one process with local SQLite and no configured
Redis/shared rate-limit store. The limiter therefore uses process-local
`memory://` storage. This is sufficient for the current topology, but it is
not correct for multiple workers or horizontally scaled API containers.

The key is the direct peer address from `get_remote_address`. Forwarded
headers are deliberately not trusted by the application. A reverse proxy
must therefore either be the only public rate-limit boundary or be followed
by an explicit trusted-proxy/keying decision before scale-out.

## Route policy

| Route class | Current policy | Key/storage |
|---|---:|---|
| All routes without a more specific decorator, including authenticated CRUD and health checks | 100/minute | direct peer IP / process-local memory |
| Register, login, refresh, logout | 10/minute | direct peer IP / process-local memory |
| Session check | 60/minute | direct peer IP / process-local memory |
| CV preview | 10/minute | direct peer IP / process-local memory |
| AST/HTML render, photo upload | 30/minute | direct peer IP / process-local memory |
| PDF render/export, PDF import, application CV generation | 5/minute | direct peer IP / process-local memory |

The more specific route decorators take precedence over the global default.
The policy does not key by email or user ID because most abuse-sensitive
endpoints are reachable before authentication, and account identifiers would
permit an attacker to distribute load across accounts. Authenticated user
quotas can be added later as a separate product policy.

## Decision

Install `SlowAPIMiddleware` whenever the production/development limiter is
enabled, retain the existing cost-class decorators, and use a 100/minute
default for uncovered routes. Keep `memory://` and direct-peer keying explicit
while the supported deployment remains one process. Rate-limit failures use
SlowAPI's normal `429` response and headers; no fail-open fallback is added.

## Implementation

`api/app/app.py` now installs the middleware for the real limiter. Auth logout
and session endpoints have explicit limits, and `api/app/core/rate_limit.py`
keeps the storage and keying assumptions visible. The frontend does not retry
429 responses.

## Verification

An ASGI probe against the application confirmed the global 100/minute limit
and its headers. Focused frontend tests cover the auth client's refresh
single-flight behavior. Full backend integration verification remains blocked
in the available Python 3.14 environment because `aiosqlite` hangs while
opening an async SQLite connection; run the migration/auth suite under the
project's supported Python 3.12 runtime.

## Follow-up

Before enabling multiple Uvicorn workers, horizontal scaling, or a deployment
where all traffic arrives through a proxy, add shared storage (for example,
Redis), configure a trusted proxy chain, and add a multi-worker integration
test. Revisit separate per-user limits for authenticated expensive operations
at that point.
