---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KYZ1XG23G90A9XDRGPRJSQQ0
TYPE: task
STATUS: PROPOSED
SUMMARY: '7 test cases were defined in the plans but never written'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- testing
- gap
RELATIONS:
  related:
  - ADR-01KYZ1XG9EWRX1VXY30CRCTMJH
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:18:34.179907+00:00'
UPDATED_AT: '2026-08-01T16:18:34.179907+00:00'
---

# Incomplete test suite

## Background

7 test cases were defined in the plans but never written

The following tests exist in COMPLETED.md but were never implemented:
- T11.2: Vitest — SectionPreviewPanel renders with per-instance styles applied
- T11.3: Vitest — section-{type} class present on preview wrapper
- T11.4: Vitest — template change strips per-instance styles
- T11.5: Pytest — backend renders per-instance styles
- ~~T51: Pytest/TS — auto-save debounces correctly (unit)~~ — **MOOT: auto-save removed (ADR-004)**
- T53: Vitest — PDF export trigger + success/fail handling
- ~~T54: Vitest — auto-save debounced save fires at correct interval~~ — **MOOT: auto-save removed (ADR-004)**

**Remaining:** 5 tests (T11.2–T11.5, T53). 2 tests (T51, T54) mooted by manual-save ADR.

Additionally:
- Phase 12 tests (U20, U21) were explicitly cancelled
- Phase 2.7 integration tests are pending
- Phase 5.8 E2E test is pending

*Migrated from SCHEMA 2 entry 001-incomplete-test-suite.md (status OPEN) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
