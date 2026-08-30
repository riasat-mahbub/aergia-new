---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M17YJ3500AF0MCDSB6NKE9GT
TYPE: feature
STATUS: PLANNED
PRIORITY: High
SEVERITY: High
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS:
- security
- auth
RELATIONS:
  depends_on:
  - TASK-01M17YJ7VRRRGSWX4WHFWAQ6DK
AFFECTS:
  files:
  - api/app/config.py
  - api/app/core/auth.py
  - api/app/core/deps.py
  - api/app/models/user.py
  - api/app/routes/auth.py
  - api/app/services/auth.py
  - api/alembic/versions
  - api/tests/conftest.py
  - api/tests/test_auth.py
  - web/src/lib/api/client.ts
  - web/src/lib/store/authStore.ts
  - web/src/App.tsx
  - web/src/components/common/ProtectedRoute.tsx
  - scripts/smoke.sh
LINKS:
  plan: local://2026-08-29-authentication-lifecycle-hardening.md
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-29T23:44:28.320213+00:00'
UPDATED_AT: '2026-08-29T23:44:28.320213+00:00'
---

# Authentication lifecycle hardening

## Background

Address authentication lifecycle reliability and security gaps: single-flight refresh, boot-time session recovery, logout independent of access-token validity, per-session refresh tokens, production configuration validation, and regression coverage.

## Investigation

The existing authentication feature is marked DONE, but the lifecycle audit
identified follow-up reliability and hardening work around concurrent refresh,
boot-time recovery, logout semantics, per-session state, and production flags.
Rate limiting is intentionally separated into a prerequisite investigation
because the current default-limit wiring and deployment topology are not yet
established.

## Decision

Pending the rate-limit investigation and the migration strategy for existing
refresh tokens. The target is cookie-first authentication with per-session
refresh state and a single-flight browser refresh path.

## Implementation

See `docs/plans/2026-08-29-authentication-lifecycle-hardening.md` for the
step-by-step delivery plan.

## Verification

Not started. Required gates include fresh-database backend tests, concurrent
refresh/session tests, frontend interceptor tests, CSRF/configuration tests,
and live auth smoke coverage.

## Follow-up

Consider password recovery/email verification and immediate access-token
revocation as separate product/security work if the app becomes multi-user or
internet-facing.
