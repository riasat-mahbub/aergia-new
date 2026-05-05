---
ID:             015
TYPE:           feature
NAME:           Manual save system
SUMMARY:        Explicit manual save replacing unreliable auto-save
STATUS:         CLOSED
TAGS:           save, ux, phase-7
LINKS:          bug=001-autosave-race-condition
---

## Description

Replaced auto-save with a predictable manual save system:
- "Save" button with disabled state when no changes exist
- Unsaved indicator: orange dot + "Unsaved changes" label
- Ctrl+S keyboard shortcut triggers save
- `useBlocker` for save-on-navigate (awaits pending save, then proceeds)
- `beforeunload` event handler warns about unsaved changes
- Toast feedback: "Saved!" for 2s after successful save
- Last-saved timestamp display

## Status

Complete.
