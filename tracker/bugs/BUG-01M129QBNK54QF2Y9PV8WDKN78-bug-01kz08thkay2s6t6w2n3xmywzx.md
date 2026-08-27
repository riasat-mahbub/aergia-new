---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M129QBNK54QF2Y9PV8WDKN78
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
  - BUG-01M129QBNK54QF2Y9PV8WDKN77
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-02T16:40:55.549573+00:00'
UPDATED_AT: '2026-08-02T16:40:55.549573+00:00'
---

# BUG-01KZ08THKAY2S6T6W2N3XMYWZX

## Background

Upgraded DateField to a real calendar (react-day-picker v10) with a popup trigger. The Firefox showPicker() workaround is no longer needed since the library renders its own popup. Value is still YYYY-MM (formatDateRange unchanged). 18 DateField tests pass; 1927 frontend tests pass; build succeeds; browser smoke confirms Start/End dates emit YYYY-MM, current toggle disables the picker, and the end-to-end preview renders correctly.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from BUG-01KZ1NK4ZXY2GN3KH8H0JDK8DY during the schema-4 cutover. -->
