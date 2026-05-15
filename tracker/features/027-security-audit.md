---
ID: 027
TYPE: feature
NAME: Comprehensive security audit
STATUS: OPEN
TAGS: security, deferred
---

## Description

Perform a comprehensive security review of the application:

- Content-Security-Policy header (preview renders user-controlled section data as raw HTML)
- Strict-Transport-Security for HTTPS deployments
- Referrer-Policy to prevent CV data leakage in Referer headers
- Input validation hardening (section data shapes, file uploads)
- Auth token handling review (refresh rotation completeness, storage patterns)
- Rate limiting strategy for production deployment

Captured from architectural review 2026-07-26.
