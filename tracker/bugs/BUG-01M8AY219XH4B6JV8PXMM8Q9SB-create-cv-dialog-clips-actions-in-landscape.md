---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M8AY219XH4B6JV8PXMM8Q9SB
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: High
EFFORT: S
OWNER: null
CONFIDENCE: High
TAGS:
- frontend
- responsive
- dialogs
RELATIONS:
  related:
  - TASK-01M1YH547G44R95DN16G9AXGJN
AFFECTS:
  files:
  - web/src/shared/ui/Modal.tsx
  - web/src/features/cvs/components/CreateCvModal.tsx
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T03:23:18.205452+00:00'
UPDATED_AT: '2026-11-26T05:59:17.557+00:00'
---

# Create CV dialog clips its actions on short viewports

## Background

The shared dialog caps its height relative to the viewport and clips overflow. Create New CV has a template list and action footer without a scrollable body.

## Investigation

1. Open **My CVs → + New CV** in a 740 × 360 viewport.
2. Fill the title and try to reach **Cancel** and **Create** by scrolling inside the dialog.

**Actual.** The modal panel is 328 px tall and its content needs 486 px. Both actions are below the clipped edge. The body has no visible scroll surface.

**Expected.** All fields, options, and actions are reachable by touch and keyboard in a short viewport. The dialog keeps its working focus and dismissal behavior as the content scrolls.

## Verification

Reproduced in Chromium on commit `78f71d2`. The modal bottom was at y=344 and the Create button began at y=440. The outer panel computed to `overflow-y: hidden`.

Fixed in [the short-viewport layout task](../tasks/TASK-01M8B5WGVA1HRQPP5AY9WAHQ35-keep-create-cv-actions-visible-on-short-viewports.md). Chromium confirmed the heading, Cancel, and Create stayed visible while scrolling at 740 × 360. A keyboard-only submission opened the builder with the last system template. Resizing through portrait and desktop preserved the form state.
