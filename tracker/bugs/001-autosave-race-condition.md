---
ID:             001
TYPE:           bug
NAME:           Auto-save race conditions & stale data
SUMMARY:        Auto-save with debounce caused race conditions, stale data references, and unreliable persistence
STATUS:         CLOSED
TAGS:           save, race-condition, debounce, stale-data
LINKS:          fix-commit=bd26616, attempts=3
---

## Description

The auto-save system used debounced saves (3s) with Zustand store subscriptions.
This led to three distinct categories of bugs, each requiring a separate fix attempt:

1. Deep-compare issues caused saves to fire on unchanged data
2. Race conditions between concurrent save promises caused data loss
3. Save-on-navigate used stale refs and missed pending saves

## Resolution

Replaced auto-save entirely with a manual save system:
- Explicit "Save" button with disabled state when no changes exist
- Unsaved changes indicator (orange dot + "Unsaved changes" label)
- Ctrl+S keyboard shortcut
- `useBlocker` for save-on-navigate (awaits pending save before proceeding)
- `beforeunload` event handler to warn about unsaved changes
- Ref-based data tracking (`instancesRef`, `customizationsRef`, `pendingSaveRef`, `instancesForUnloadRef`)

### Commit
`bd26616` — Replace autosave with manual save system
