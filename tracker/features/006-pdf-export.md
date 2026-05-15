---
ID:             006
TYPE:           feature
NAME:           PDF export via Playwright
SUMMARY:        In-process PDF generation using Playwright Chromium headless
STATUS:         CLOSED
TAGS:           pdf, phase-7
LINKS:          phase=COMPLETED.md-phase-7
---

## Description

Server-side PDF export:
- Playwright Chromium runs in-process (no external service)
- Renders the same HTML as the preview to guarantee visual match
- Async `render_pdf` and sync `render_pdf_sync` convenience functions
- Uses the new IR-based renderer pipeline
- PDF content matches CV data exactly

## Status

All Phase 7 tasks complete. Tests: T49-T50 pass, T52 pass. T51/T53/T54 incomplete.
