---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M8B5WGVA1HRQPP5AY9WAHQ35
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: High
TAGS:
- frontend
- responsive
- dialogs
RELATIONS:
  related:
  - BUG-01M8AY219XH4B6JV8PXMM8Q9SB
  - TASK-01M8AY219XV55JCZZ8B84QANVK
AFFECTS:
  files:
  - web/src/shared/ui/Modal.tsx
  - web/src/features/cvs/components/CreateCvModal.tsx
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T05:40:06.122587+00:00'
UPDATED_AT: '2026-11-26T05:59:17.557+00:00'
---

# Keep Create CV actions visible on short viewports

## Background

Implementation plan for [BUG-01M8AY219XH4B6JV8PXMM8Q9SB](../bugs/BUG-01M8AY219XH4B6JV8PXMM8Q9SB-create-cv-dialog-clips-actions-in-landscape.md).

## Investigation

The shared panel caps its height at the viewport minus its outer margin and clips overflow. Create New CV currently puts its title field, template options, and footer in the same unbounded content block. At 740 × 360, the footer falls below the panel.

## Decision

Give Create New CV a bounded flex column with an independently scrolling form body. Keep the heading and action footer visible so selecting a template and completing the form work in landscape.

## Implementation

1. Add an opt-in panel layout to `Modal.tsx` for a fixed heading and footer around a scrollable body. Use the existing viewport margin and panel padding. Use a dynamic viewport-height cap with a standard viewport-height fallback. Let the panel size naturally with short content.
2. In `CreateCvModal.tsx`, place the heading and action footer outside the scroll area as `shrink-0` flex items. Put the title field and template list in a single `min-h-0 flex-1 overflow-y-auto` body. Verify padding leaves room for visible focus indicators.
3. Keep the existing dialog heading and title label associations, initial title focus, template selection, submission, Escape handling, and focus restoration. The modal panel remains the focus-trap boundary.
4. Apply the layout only to Create New CV. Check a confirmation dialog and the application form, which already has a scrollable body, to confirm their scrolling and focus behavior.

## Verification

- At 740 × 360, open Create New CV with all shipped templates. Confirm Create and Cancel remain visible while scrolling to the last template by wheel or touch-equivalent input.
- With keyboard only, verify initial Title focus, template selection, forward and reverse Tab, and focus restoration after Escape and Cancel.
- Submit a CV using the last template from the landscape layout. Confirm the builder opens with that template.
- Check the 390 × 844 portrait and 1440 × 900 desktop layouts. Rotate or resize with the dialog open and verify that the title and selected template survive and the footer remains reachable.

Chromium verified that the form body scrolls at 740 × 360 while the heading and footer stay visible. Title received initial focus, Tab and Shift+Tab wrapped within the dialog, and Escape and Cancel restored focus. Keyboard selection and submission created a CV with the last system template. The title and selection survived resizing through 390 × 844 and 1440 × 900. Application edit and delete confirmation also passed their focus and dismissal checks.
