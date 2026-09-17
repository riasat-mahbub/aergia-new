---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M2HGK4D1W9EP1B6KBS23FJDC
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
  - TASK-01M2HE156EGV30WRCWHNY9YBEX
AFFECTS:
  files:
  - portfolio-showcase/README.md
  - portfolio-showcase/src/capture.py
  - portfolio-showcase/src/config.py
  - portfolio-showcase/src/encode.py
  - portfolio-showcase/src/overlays.py
  - portfolio-showcase/src/seed.py
  - portfolio-showcase/tests/test_storyboard.py
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-15T03:08:28.449420+00:00'
UPDATED_AT: '2026-09-15T03:08:28.449420+00:00'
---

# Polish showcase poster and application handoff

## Background

Finished the portfolio showcase polish: the opening card and poster now use Aergia's application palette, the recording begins on a fully painted poster with encoded-away preroll, title cards hide the cursor, and the disposable seed creates a valid tailoring session. Capture now requires the latest-session request to return 200 and rejects the prior visible error state. Regenerated and visually verified all outputs.

## Investigation

The capture navigated to the dashboard before installing its title-card
overlay, allowing the application shell to appear at the start of the raw
recording. The title card also used a navy gradient rather than the product's
application tokens. The application page requested its latest tailoring
session; because the disposable seed had none, the expected 404 was surfaced
by the shared API reporter as a visible error toast.

## Decision

Render the title card on a standalone local page before any product navigation,
trim a short stable preroll from every encoded animation, and use the canonical
emerald, mint, slate, and off-white palette. Seed a genuine short-lived
tailoring session and make its successful lookup a capture invariant.

## Implementation

Restyled title cards with Aergia palette values and hid the synthetic cursor
while either card is visible. Added a 750 ms capture preroll that all media
encoders remove, with the poster generated from the normalized MP4. Added a
disposable tailoring session after application CV generation and a browser
response guard that aborts capture on a non-200 latest-session response or the
previous missing-session message.

## Verification

`api/.venv/bin/pytest -q portfolio-showcase/tests` passed (6 tests).
`api/.venv/bin/ruff check portfolio-showcase/src portfolio-showcase/tests`
passed, as did `git diff --check`. The escalated disposable dry run and full
capture/encode run both passed. The new 1280x800 MP4 is 63.33 seconds and 2.1
MB; MP4, WebM, GIF, and poster outputs were regenerated. Inspection of the
first encoded frame and poster confirmed the Aergia palette with no preceding
app frame, and inspection of the application and builder frames confirmed the
error toast is absent.

## Follow-up
