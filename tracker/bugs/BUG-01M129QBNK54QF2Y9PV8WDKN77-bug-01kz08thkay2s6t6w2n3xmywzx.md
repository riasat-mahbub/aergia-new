---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M129QBNK54QF2Y9PV8WDKN77
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: High
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01M129QBNK54QF2Y9PV8WDKN76
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-02T03:42:12.776642+00:00'
UPDATED_AT: '2026-08-02T03:42:12.776642+00:00'
---

# BUG-01KZ08THKAY2S6T6W2N3XMYWZX

## Background

Replaced <input type="month"> with two native <select> elements (Year + Month) so the date picker works in Firefox. Value is still the YYYY-MM string — no downstream changes needed. 15 DateField tests pass; 1926 frontend tests pass; 22 backend tests pass; browser smoke confirms year+month → YYYY-MM emission and end-to-end preview rendering.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from BUG-01KZ091998D3AX2Q7104H2YJHC during the schema-4 cutover. -->
