---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M2HE156EGV30WRCWHNY9YBEX
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01M2HBC8GZ6GC3ZQYT4QADS3SA
AFFECTS:
  files:
  - portfolio-showcase/README.md
  - portfolio-showcase/config/storyboard.json
  - portfolio-showcase/fixtures/demo-data.json
  - portfolio-showcase/fixtures/source-cv.html
  - portfolio-showcase/run.py
  - portfolio-showcase/src/capture.py
  - portfolio-showcase/src/config.py
  - portfolio-showcase/src/overlays.py
  - portfolio-showcase/src/seed.py
  - portfolio-showcase/tests/test_storyboard.py
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-15T02:23:42.287016+00:00'
UPDATED_AT: '2026-09-15T02:23:42.287016+00:00'
---

# Refine portfolio showcase interactions

## Background

Refined the portfolio tour so the cursor is centered on each target with a click ripple, the same imported Modern CV remains visible through editing and customization, customization effects appear in the live preview, and the flow opens the Applications tab and Northstar Systems application. Regenerated and visually verified the portfolio outputs.

## Investigation

The original recording mixed CV variants, relied on synthetic cursor movement
that could drift from the browser's final target geometry, and opened an
application detail URL without showing the list interaction. Its customization
scene also did not hold long enough on an obvious visual change.

## Decision

Keep the visible story anchored to one imported Modern CV. Measure targets
immediately before clicking, animate a click ripple at that point, apply
high-contrast customization values, and navigate to application detail through
the visible Applications UI.

## Implementation

Added a parser-friendly fictional source CV that is rendered to a temporary PDF
for each run. Updated capture helpers to scroll, remeasure, center the cursor,
and ripple-click each target. Extended the tour through visible heading and
background changes, the Applications tab, and the Northstar Systems card while
retaining Modern template continuity.

## Verification

`api/.venv/bin/pytest -q portfolio-showcase/tests` passed (4 tests).
`api/.venv/bin/ruff check portfolio-showcase/src portfolio-showcase/tests`
passed. Both the dry run and full capture/encode completed. The generated
1280x800 MP4 is 63.63 seconds; MP4, WebM, GIF, and poster artifacts were
generated. Contact-sheet inspection confirmed aligned click feedback, visible
purple typography and lavender section background changes, Applications list
navigation, and the opened Northstar Systems record.

## Follow-up
