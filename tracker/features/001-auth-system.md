---
ID:             001
TYPE:           feature
NAME:           Auth (register/login/refresh/logout)
SUMMARY:        Full authentication system with JWT tokens and bcrypt password hashing
STATUS:         CLOSED
TAGS:           auth, phase-1
LINKS:          phase=COMPLETED.md-phase-1
---

## Description

Complete authentication flow with:
- Register (email + password with Zod validation)
- Login (returns access + refresh JWT tokens)
- Token refresh (15min access, 7d refresh stored as SHA-256 hash in DB)
- Logout (revokes refresh token)
- Change password
- bcrypt cost 12, JWT HS256
- Protected routes with redirect to login

## Status

All Phase 1 tasks complete including T1-T5 tests.
