---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN8P
TYPE: feature
STATUS: PROPOSED
SUMMARY: Extend IR-based renderer to output LaTeX and DOCX formats
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- future
- rendering
RELATIONS:
  related:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN8C
AFFECTS:
  files:
  - docs/plans/2026-11-26-docx-export.md
  - api/app/routes/cvs.py
  - api/app/services/docx.py
  - api/app/services/renderer/docx.py
  - api/app/services/renderer/pipeline.py
  - web/src/features/cvs/components/CVExportControl.tsx
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:11:58.482296+00:00'
UPDATED_AT: '2026-11-26T19:27:39.401+00:00'
---

# LaTeX/DOCX renderer backends

## Background

The original proposal grouped LaTeX and DOCX as formats for the former
IR renderer registry. It proposed `.tex` for academic CVs and `.docx`
for application systems that require a Word file.

Proposed future enhancement (previously OPEN in the SCHEMA 2 tracker). Tags: future.
*Migrated from SCHEMA 2 entry 022-latex-docx-export.md (status OPEN) on 2026-08-01.*

## Investigation


## Decision

The [DOCX export plan](../../docs/plans/2026-11-26-docx-export.md) uses the current AST and resolver to generate an editable, single-column Word document. The plan covers CV and linked application downloads, content preservation, and Word compatibility checks.


## Implementation

The saved CV export route serves an editable DOCX using the same AST and resolver as PDF. Its Word renderer uses native headings, paragraphs, lists, and hyperlinks in saved section order. The builder offers PDF and Word through an Export control that saves first. Application detail offers the same formats for its linked CV.

## Verification

- The renderer, route, OpenAPI, and focused PDF regression suites passed 79 tests. Eight font-size assertions in the broader PDF readability suite also failed on the baseline commit `57cf4ea`.
- Chromium verified the download headers through the same-origin gateway, keyboard and pointer exports, builder save and retry, stale export cancellation, and duplicate prevention on mobile application detail.
- Microsoft Word 16.0 build 16.0.20625 opened all three fixtures. A Word edit survived save and reopen. LibreOffice 26.8.3.1 reopened its DOCX saves and preserved heading placement, list restarts, and multipage content.
- Microsoft Open XML SDK 3.3.0 reported zero validation errors for all three generated fixtures. The production smoke gate and frontend architecture checks passed.

## Follow-up

LaTeX export is a separate proposal.

<!-- Migrated from FEAT-01KYZ1HDMJRX33A5HEPJXGQ4FC during the schema-4 cutover. -->
