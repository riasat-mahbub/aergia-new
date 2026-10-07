---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M4BWW0K45JFMJPHGW3DEQTK6
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- audit
- ats
- builder
- templates
RELATIONS: null
AFFECTS:
  files:
  - docs/cv-builder-ats-audit-2026-10-07.md
  - docs/cv-builder-ats-audit-2026-10-07-results.json
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-10-07T19:18:59.428783+00:00'
UPDATED_AT: '2026-10-07T19:18:59.428783+00:00'
---

# Audit CV builder and system templates for ATS compatibility

## Background

Audited b8e4016 with six synthetic Chromium PDFs, dual-parser extraction, source review, vendor guidance, and 155 passing focused tests. Recorded twelve prioritized findings and an implementation roadmap in docs/cv-builder-ats-audit-2026-10-07.md; product behavior unchanged.

## Investigation

Inspected frontend builder and shared editors, AST builders, seeded manifests,
HTML/PDF rendering, and ATS guidance. Six synthetic CV PDFs reproduce Modern
sidebar interleaving and a wrapped visible-URL recovery failure. Classic and
Minimal pass the structural recovery checks for both fixture lengths. Pure
reproductions confirm date-preset inconsistencies, a compound-title false
positive, hidden-heading diagnostic gaps, and inert profile controls.

Consulted the completed project readability fix
BUG-01M3HTTAWH8Y9AWSYA8AVRPY3R; the sidebar limitation was already documented.

## Decision

Document findings and proposed improvements without changing behavior, URLs,
API payloads, database structure, or editor preferences. Retain the canonical
renderer and distinguish local recovery from actual third-party ATS testing.

## Implementation

Added a report with twelve findings (three P1, nine P2), provisional interface
assessment, verified vendor sources, template comparison, phased roadmap,
and acceptance criteria. Added generated synthetic evidence summary JSON.

## Verification

155 focused backend tests passed. Six production-pipeline PDFs were inspected
with pdfplumber and PDFium, the existing scanner, and three PDF screenshots.
All fixtures stay within physical page width and recover entry dates,
email/phone, and clickable links. Ran the Impeccable detector once; its width
transition warning is documented separately as minor polish.

No live vendor ATS or authenticated desktop/mobile UI trial was performed.

## Follow-up

Implement the report's phases as separately scoped work. Broaden synthetic
career/language fixtures and verify keyboard workflows in the running app.
