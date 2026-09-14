---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M2H0N7NSKJ2NK0PA3V70HKV4
TYPE: bug
STATUS: DONE
PRIORITY: Medium
SEVERITY: Low
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS:
- frontend
- library
- rich-text
RELATIONS: null
AFFECTS:
  files:
  - web/src/shared/cv-editor/section-editors/rich-text/RichTextEditor.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-14T22:30:00.121573+00:00'
UPDATED_AT: '2026-09-14T22:30:00.121573+00:00'
---

# Typing in a library field transfers focus to rich text

## Background

After typing in an ordinary Project field in the library editor, focus moves to the rich-text Description after the first character. Lexical retains its DOM selection when its contenteditable blurs; a later document selectionchange restores that selection and steals focus.

## Investigation

The project row, modal, and rich-text value remain stable when Name changes.
The focus jump comes from Lexical retaining its DOM selection after the
contenteditable loses focus. Typing in the adjacent Name input raises a
document `selectionchange`; Lexical then reapplies the stale Description
selection and focuses its root.

## Decision

Clear Lexical's selection when focus leaves the rich-text control. Keep the
selection when focus moves to a toolbar control so formatting remains usable.

## Implementation

Added a Lexical blur-command handler that clears the selection when focus
moves outside the rich-text wrapper. The OnChange plugin now ignores
selection-only updates so clearing focus does not emit an unchanged document
value to the parent editor.

## Verification

Reproduced the original failure in headless Chromium with an existing Project
payload. After the change, typed `WXYZ` at the end of Name remained intact and
Name retained focus. `npm run typecheck` passed. `npm run lint --
src/shared/cv-editor/section-editors/rich-text/RichTextEditor.tsx` passed with
nine existing hook-dependency warnings in unrelated files.

## Follow-up
