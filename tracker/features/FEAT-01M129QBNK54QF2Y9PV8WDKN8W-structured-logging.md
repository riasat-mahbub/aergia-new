---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN8W
TYPE: feature
STATUS: PROPOSED
SUMMARY: ''
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- observability
- deferred
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:11:58.915270+00:00'
UPDATED_AT: '2026-08-01T16:11:58.915270+00:00'
---

# Structured logging

## Background

Replace default uvicorn logging with structured logging for better observability:

- Add request ID generation and propagation (correlation IDs) across the request lifecycle
- Configurable log levels via environment variable
- Consider structlog or stdlib logging with JSON formatter
- Add access logging with request duration, status code, path, user identifier
- Avoid logging sensitive data (passwords, token bodies)

Captured from architectural review 2026-07-26.

Proposed future enhancement (previously OPEN in the SCHEMA 2 tracker). Tags: observability, deferred.

*Migrated from SCHEMA 2 entry 028-structured-logging.md (status OPEN) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from FEAT-01KYZ1HE23VRV2ZH5MB4HGBW75 during the schema-4 cutover. -->
