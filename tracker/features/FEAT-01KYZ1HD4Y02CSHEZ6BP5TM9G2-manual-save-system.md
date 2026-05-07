---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KYZ1HD4Y02CSHEZ6BP5TM9G2
TYPE: feature
STATUS: DONE
SUMMARY: 'Explicit manual save replacing unreliable auto-save'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- save
- ux
- phase-7
RELATIONS:
  fixes:
  - BUG-01KYZ1D1S29KD6NWB2R9J01GWF
  implements:
  - ADR-01KYZ1XG9EWRX1VXY30CRCTMJH
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:11:57.982382+00:00'
UPDATED_AT: '2026-08-01T16:11:57.982382+00:00'
---

# Manual save system

## Background

Explicit manual save replacing unreliable auto-save

Replaced auto-save with a predictable manual save system:
- "Save" button with disabled state when no changes exist
- Unsaved indicator: orange dot + "Unsaved changes" label
- Ctrl+S keyboard shortcut triggers save
- `useBlocker` for save-on-navigate (awaits pending save, then proceeds)
- `beforeunload` event handler warns about unsaved changes
- Toast feedback: "Saved!" for 2s after successful save
- Last-saved timestamp display

*Migrated from SCHEMA 2 entry 015-manual-save-system.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation


## Verification

Complete.

## Follow-up
