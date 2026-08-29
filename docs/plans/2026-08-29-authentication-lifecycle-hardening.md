# Authentication lifecycle hardening

Tracker: `FEAT-01M17ZNMAF0R3B2V13GBWKJ6W6`

Rate-limit investigation: `TASK-01M17ZNFD1H4K69ZXCQC5ZG9VZ`

Status: implementation complete in the isolated `auth-hardening` worktree;
backend integration verification is pending a supported Python 3.12 runtime.

## Objective

Make cookie-based authentication reliable across expired access tokens,
concurrent API failures, multiple browser sessions, logout, and production
configuration. Preserve the current security baseline: bcrypt password
hashing, HttpOnly cookies, refresh-token hashing, JWT issuer/audience checks,
and CSRF protection.

Rate limiting is a gated investigation. The deployment model and endpoint
policy are now documented in `ADR-01M17ZKK02PDCJE0S199HDRVBA`; the selected
single-process baseline is implemented, while shared storage and trusted
proxy keying remain explicit scale-out follow-ups.

## Non-goals

- Do not reintroduce password change without a proper password-reset design.
- Do not persist provider API keys in browser storage or the account profile.
- Do not replace cookie auth with localStorage bearer tokens.
- Do not add a distributed dependency solely for rate limiting before the
  investigation confirms that the deployment model requires it.

## Delivery protocol

For each step:

1. Search related tracker entries and inspect `tracker affects` results.
2. Implement only the step in scope.
3. Run focused backend/frontend tests and static checks.
4. Commit the implementation separately.
5. Update the relevant tracker entry with the result.
6. Run `tracker rebuild && tracker validate`.
7. Commit the tracker update separately.

Keep the implementation and tracker commits unsquashed. Resolve the existing
backend migration/test bootstrap problem before treating the full verification
suite as a release gate.

## Step 1 — Investigate and design rate limiting (complete)

Tracker: `TASK-01M17ZNFD1H4K69ZXCQC5ZG9VZ`

Files to inspect:

- `api/app/app.py`
- `api/app/core/rate_limit.py`
- authenticated and expensive routes under `api/app/routes/`
- `docker-compose.yml`, `dev.sh`, and deployment documentation
- existing smoke and integration tests

Questions to answer before implementation:

- Is SlowAPI's `default_limits` active in the current application wiring, or
  are only decorated endpoints limited?
- Which limits apply to unauthenticated authentication endpoints versus
  authenticated user actions?
- Should keys use source IP, normalized account identifier, authenticated user
  ID, or a composed key? How will trusted proxy headers be configured safely?
- Is the supported deployment one process, multiple workers, or horizontally
  scaled? Is in-memory storage sufficient, or is shared storage required?
- Which operations need separate cost classes: login/register/refresh,
  session/logout, CRUD writes, PDF/render, import, LLM calls, and generation?
- What response headers, observability, and client behavior are required when
  a limit is exceeded?

Deliverables:

- A short ADR or decision section documenting keying, storage, route classes,
  default limits, proxy assumptions, and failure behavior.
- A route coverage table showing the expected policy for every mutating and
  expensive endpoint.
- Focused tests proving the current behavior and the selected policy,
  including multi-worker/shared-storage behavior if applicable.

Until this step is complete, retain the working per-route limits on login,
registration, refresh, import, render, and PDF endpoints.

## Step 2 — Establish per-session refresh-token state (implemented)

Files in scope:

- `api/app/models/user.py`
- new Alembic migration and auth-session model
- `api/app/core/auth.py`
- `api/app/services/auth.py`
- `api/app/routes/auth.py`
- `api/app/core/deps.py`

Work:

- Add an `auth_sessions` table with a session ID, user ID, hashed refresh
  token, expiry, created/last-used timestamps, and revocation state.
- Bind refresh tokens to a session identifier and keep rotation atomic.
- Define reuse behavior for an old refresh token: reject it and, if the token
  family model is selected, revoke the affected session family.
- Make login create a session instead of overwriting one global user hash.
- Make logout revoke the current session; leave room for revoke-all-sessions
  as a later account action.
- Decide whether already-issued access tokens need immediate revocation. If
  required, add a session/version claim and a bounded revocation check instead
  of an unbounded token denylist.
- Define migration behavior for existing `users.refresh_token_hash` values:
  migrate them once, force reauthentication, or explicitly discard them.

## Step 3 — Make client refresh and hydration single-flight (implemented)

Files in scope:

- `web/src/lib/api/client.ts`
- `web/src/lib/store/authStore.ts`
- `web/src/App.tsx`
- `web/src/components/common/ProtectedRoute.tsx`

Work:

- Add one shared in-flight refresh promise so concurrent `401` responses
  await the same refresh operation.
- Retry each original request at most once and preserve the original failure
  when refresh is rejected.
- Make one component own initial authentication hydration.
- During boot, recover an expired access token through the refresh flow before
  declaring the user unauthenticated.
- Prevent stale hydration responses from overwriting a later login/logout.
- Ensure logout always clears local state while the server revokes the current
  refresh session independently of access-token validity.

## Step 4 — Fail closed on production auth configuration (implemented)

Files in scope:

- `api/app/config.py`
- `api/app/routes/auth.py`
- `api/app/app.py`
- deployment examples and documentation

Work:

- Validate `environment` against a normalized closed set.
- Fail startup in production if bearer-token fallback or token responses are
  enabled.
- Centralize cookie options and verify Secure, HttpOnly, SameSite, and path
  behavior for every auth response.
- Retain Origin/double-submit CSRF checks for cookie-authenticated mutations.
- Document that logout revokes refresh state while access tokens may remain
  valid until expiry unless the optional immediate-revocation decision is
  adopted.

## Step 5 — Repair verification and add regression coverage (partially verified)

Files in scope:

- `api/tests/conftest.py`
- `api/tests/test_auth.py`
- new backend auth/concurrency/rate-limit tests
- new frontend client-interceptor tests
- `scripts/smoke.sh`

First repair the migration/test bootstrap so a fresh temporary database can
run migrations and pytest without hanging. Then add tests for:

- concurrent refresh requests and refresh-token rotation;
- reload with an expired access token and valid refresh token;
- logout with an expired access token;
- multiple sessions and per-session revocation;
- invalid signature, issuer, audience, type, expiry, and reuse cases;
- CSRF rejection and valid Origin/token cases;
- production configuration fail-closed behavior;
- every selected rate-limit route, key, storage, and `Retry-After` contract;
- frontend single-flight refresh and stale hydration protection.

Verification gates:

- backend pytest on a fresh database;
- backend Ruff;
- frontend tests, full lint, build, and codegen check;
- live smoke test for login, refresh, logout, protected API access, and the
  selected rate-limit policy.

## Acceptance criteria

- Concurrent expired requests do not cause a valid session to be redirected
  to login because of refresh-token rotation.
- A page reload with a valid refresh session restores authentication after the
  access token expires.
- Logout revokes the current refresh session and clears both auth cookies even
  when the access token is expired.
- Session behavior is explicit: multiple sessions either work independently or
  are intentionally rejected and tested as a product decision.
- Production cannot start with token exposure or bearer fallback enabled.
- Rate-limit behavior is documented, tested, observable, and correct for the
  actual deployment topology.
- The complete verification suite runs to completion on a fresh database.
