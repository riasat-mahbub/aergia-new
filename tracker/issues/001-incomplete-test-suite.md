---
ID:             001
TYPE:           issue
NAME:           Incomplete test suite
SUMMARY:        7 test cases were defined in the plans but never written
STATUS:         OPEN
TAGS:           testing, gap
---

## Description

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
