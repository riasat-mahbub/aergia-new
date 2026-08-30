---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M18DNPBJZK8HV7HPT6ZS4MDV
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- premium
- quota
- auth
RELATIONS:
  supersedes:
  - FEAT-01M18D6P7HDPPMNPNRDKE2RKH0
  depends_on:
  - FEAT-01M189ZDW7JE07N01TMGCXJHTF
AFFECTS:
  files:
  - api/app/models/user.py
  - api/alembic/versions/f1a2b3c4d5e6_add_account_tier.py
  - api/app/services/quotas.py
  - api/app/config.py
  - api/app/schemas/auth.py
  - api/app/routes/auth.py
  - web/src/lib/api/auth.ts
  - web/src/lib/store/authStore.ts
  - api/tests/test_abuse_prevention.py
  - api/tests/test_auth.py
  - web/src/lib/store/__tests__/authStore.test.ts
  - .env.example
  - DEPLOY.md
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-30T04:08:34.930509+00:00'
UPDATED_AT: '2026-08-30T04:08:34.930509+00:00'
---

# Premium account tiers with quota entitlements

## Background

Implemented persisted free/premium tiers, migrated users with a free default, made atomic application/CV reservations tier-aware, exposed account_tier in /auth/session and frontend auth state, removed the temporary quota bypass, and promoted exactly one dev account (a@a.com). Verification passed for frontend tests/build/codegen, focused backend tests, Ruff, compileall, and migration SQL; DB-backed pytest is still blocked by the known Python 3.14/aiosqlite hang.

## Investigation

The quota counters are already transactional and stored on `users`, so a
persisted tier can be folded into the existing conditional counter updates.
The development database contains exactly one `a@a.com` account with existing
CV data above the free cap; a user-ID bypass would keep the account outside the
real entitlement model.

## Decision

Use a string-backed `AccountTier` with `free` as the migration and registration
default and `premium` as the only expanded tier. Premium accounts keep both
counters accurate but are allowed to reserve beyond the free thresholds. Keep
tier assignment operator-controlled until a billing or membership workflow is
explicitly scoped.

## Implementation

Added the account tier column and migration, removed the temporary quota bypass
setting, made both quota reservations tier-aware under the existing SQLite
`BEGIN IMMEDIATE` transaction, exposed the tier from `/auth/session`, and
stored it in the frontend auth state. Applied the migration to the dev database
and promoted the exact `a@a.com` row to `premium`.

## Verification

Frontend tests (351), auth-store tests, production build, codegen drift check,
focused Turnstile/rate-limit tests, Ruff, compileall, and migration SQL checks
pass. The online Alembic command was not usable on this host because Python
3.14/aiosqlite hangs during database connection; the validated migration SQL
was applied directly in a SQLite write transaction. DB-backed pytest remains
subject to the same host runtime limitation.

## Follow-up

Add a controlled tier-management or billing integration only when premium
entitlements need to be customer-managed; do not add a public self-promotion
endpoint.
