---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNEM
TYPE: task
STATUS: PROPOSED
PRIORITY: High
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- parser
- fix
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-11T22:45:08.340619+00:00'
UPDATED_AT: '2026-08-11T22:45:08.340619+00:00'
---

# pdf-parser: bare-handle contact regex

## Background

Task 2 of plan. The contact-line regexes (URL_RE, LINKEDIN_RE, GITHUB_RE) only fire on scheme-prefixed URLs. Real-world resumes use middot-separated bare handles and bare domains. Add a contact-line bare-token pass in _extract_profile_fields: bare handles in known social host families become social links; bare <host>.<tld> becomes site_url. New tests in api/tests/test_parsers.py.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from TASK-01KZSG0GKM1YW4TVFK8N8FYSJT during the schema-4 cutover. -->
