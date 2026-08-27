---
SCHEMA: 4
FORMAT: project-tracker
ID: ADR-01M129QBNK54QF2Y9PV8WDKN6S
TYPE: adr
STATUS: DONE
SUMMARY: Why auto-save was replaced with an explicit manual save system
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- adr
- architecture
RELATIONS:
  related:
  - BUG-01M129QBNK54QF2Y9PV8WDKN6X
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:18:34.414186+00:00'
UPDATED_AT: '2026-08-01T16:18:34.414186+00:00'
---

# ADR: Manual save over auto-save

## Background

Why auto-save was replaced with an explicit manual save system

The original auto-save system used a 3-second debounce triggered by Zustand
store subscriptions. It had persistent reliability issues despite 3 attempts
at fixing:
1. Deep-compare to stabilize data references
2. Save immediately on drag-end + save-on-navigate safety net
3. Ref-based guards for pending saves

Each fix introduced new edge cases (race conditions, stale closures, missed saves).

*Migrated from SCHEMA 2 entry 004-adr-manual-save.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision

Replace with an explicit manual save system:
- Visible "Save" button, disabled when no changes
- Ctrl+S keyboard shortcut
- `useBlocker` for save-on-navigate (awaits pending save)
- `beforeunload` event handler
- Unsaved changes indicator (orange dot)

### Consequences

- More predictable: user controls when data is persisted
- Simpler mental model: no background magic
- Slightly worse UX: user must explicitly save
- Eliminated 3 rounds of auto-save bug fixes

### Date

2026-06-27 (Phase 7)

## Implementation


## Verification


## Follow-up

<!-- Migrated from ADR-01KYZ1XG9EWRX1VXY30CRCTMJH during the schema-4 cutover. -->
