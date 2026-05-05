---
ID:             004
TYPE:           issue
NAME:           ADR: Manual save over auto-save
SUMMARY:        Why auto-save was replaced with an explicit manual save system
STATUS:         CLOSED
TAGS:           adr, architecture
---

## Description

### Context

The original auto-save system used a 3-second debounce triggered by Zustand
store subscriptions. It had persistent reliability issues despite 3 attempts
at fixing:
1. Deep-compare to stabilize data references
2. Save immediately on drag-end + save-on-navigate safety net
3. Ref-based guards for pending saves

Each fix introduced new edge cases (race conditions, stale closures, missed saves).

### Decision

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
