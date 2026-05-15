---
ID: 028
TYPE: feature
NAME: Structured logging
STATUS: OPEN
TAGS: observability, deferred
---

## Description

Replace default uvicorn logging with structured logging for better observability:

- Add request ID generation and propagation (correlation IDs) across the request lifecycle
- Configurable log levels via environment variable
- Consider structlog or stdlib logging with JSON formatter
- Add access logging with request duration, status code, path, user identifier
- Avoid logging sensitive data (passwords, token bodies)

Captured from architectural review 2026-07-26.
