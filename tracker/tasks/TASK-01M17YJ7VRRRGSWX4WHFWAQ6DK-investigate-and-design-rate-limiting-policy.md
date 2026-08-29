---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M17YJ7VRRRGSWX4WHFWAQ6DK
TYPE: task
STATUS: PLANNED
PRIORITY: High
SEVERITY: Medium
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- security
- auth
- rate-limiting
RELATIONS:
  related:
  - FEAT-01M17YJ3500AF0MCDSB6NKE9GT
AFFECTS:
  files:
  - api/app/app.py
  - api/app/core/rate_limit.py
  - api/app/routes/auth.py
  - api/app/routes/cvs.py
  - api/app/routes/applications.py
  - api/app/routes/library.py
  - api/app/routes/profile.py
  - api/app/routes/assets.py
  - api/app/routes/imports.py
  - api/app/routes/render.py
  - docker-compose.yml
  - dev.sh
  - scripts/smoke.sh
LINKS:
  plan: local://2026-08-29-authentication-lifecycle-hardening.md
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-29T23:44:33.144879+00:00'
UPDATED_AT: '2026-08-29T23:44:33.144879+00:00'
---

# Investigate and design rate limiting policy

## Background

Investigate current SlowAPI wiring and route coverage; verify whether default limits are active; define limits by endpoint cost and authentication state; decide IP, account, and proxy-aware keys; evaluate in-memory versus shared storage; test multi-worker behavior and trusted proxy configuration; document the chosen policy before changing code.

## Investigation

Initial audit found that the app stores a limiter on `app.state` and registers
the exception handler, but does not visibly install SlowAPI middleware. The
auth, render, import, and PDF endpoints have explicit decorators; several
authenticated CRUD routes do not. This must be confirmed with a focused
integration test against the installed SlowAPI version before any wiring or
limit changes.

Investigate route coverage, endpoint cost, source-IP/proxy handling, account
and user keying, in-memory versus shared storage, multi-worker behavior,
failure mode, response headers, and observability.

## Decision

Not decided. Numeric limits and the default-limit mechanism remain blocked on
the investigation deliverable.

## Implementation

No limiter implementation changes are included in this investigation task.

## Verification

Produce a route policy table and tests that demonstrate the current behavior,
then verify the selected policy in the supported deployment topology.

## Follow-up

Create or update an ADR with the chosen policy before implementing the rate
limiter changes. Keep the existing explicit auth and expensive-operation limits
until the decision is approved.
