---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KYZ1D1S29KD6NWB2R9J01GWF
TYPE: bug
STATUS: DONE
SUMMARY: 'Auto-save with debounce caused race conditions, stale data references, and unreliable persistence'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- save
- race-condition
- debounce
- stale-data
RELATIONS:
  related:
  - ADR-01KYZ1XG9EWRX1VXY30CRCTMJH
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:09:35.266223+00:00'
UPDATED_AT: '2026-08-01T16:09:35.266223+00:00'
---

# Auto-save race conditions & stale data

## Background

Auto-save with debounce caused race conditions, stale data references, and unreliable persistence

The auto-save system used debounced saves (3s) with Zustand store subscriptions.
This led to three distinct categories of bugs, each requiring a separate fix attempt:

1. Deep-compare issues caused saves to fire on unchanged data
2. Race conditions between concurrent save promises caused data loss
3. Save-on-navigate used stale refs and missed pending saves

*Migrated from SCHEMA 2 entry 001-autosave-race-condition.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation

Replaced auto-save entirely with a manual save system:
- Explicit "Save" button with disabled state when no changes exist
- Unsaved changes indicator (orange dot + "Unsaved changes" label)
- Ctrl+S keyboard shortcut
- `useBlocker` for save-on-navigate (awaits pending save before proceeding)
- `beforeunload` event handler to warn about unsaved changes
- Ref-based data tracking (`instancesRef`, `customizationsRef`, `pendingSaveRef`, `instancesForUnloadRef`)

### Commit
`bd26616` — Replace autosave with manual save system

## Verification


## Follow-up
