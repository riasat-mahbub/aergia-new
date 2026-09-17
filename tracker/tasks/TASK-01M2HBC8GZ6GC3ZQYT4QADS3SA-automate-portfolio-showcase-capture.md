---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M2HBC8GZ6GC3ZQYT4QADS3SA
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: High
TAGS:
  - showcase
  - automation
RELATIONS: null
AFFECTS:
  files:
  - portfolio-showcase/README.md
  - portfolio-showcase/config/storyboard.json
  - portfolio-showcase/fixtures/demo-data.json
  - portfolio-showcase/run.py
  - portfolio-showcase/src/capture.py
  - portfolio-showcase/src/config.py
  - portfolio-showcase/src/encode.py
  - portfolio-showcase/src/environment.py
  - portfolio-showcase/src/migrate.py
  - portfolio-showcase/src/overlays.py
  - portfolio-showcase/src/seed.py
  - portfolio-showcase/src/storyboard.py
  - portfolio-showcase/tests/test_storyboard.py
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-15T01:37:20.415312+00:00'
UPDATED_AT: '2026-09-15T01:37:20.415312+00:00'
---

# Automate portfolio showcase capture

## Background

Add a self-contained portfolio-showcase harness that seeds fictional Aergia data, records the main product flow through the public web app, and emits portfolio-ready MP4, WebM, GIF, and poster assets.

## Investigation

The showcase needs the real same-origin application flow to be convincing in
a portfolio: import, authoring, customization, Library reuse, application
matching, tailored CV generation, and PDF export. A disposable runtime keeps
the existing development database and credentials out of the recording.

## Decision

Use a root-level `portfolio-showcase/` harness driven by Playwright and
ffmpeg. Seed fictional data through the public API, authenticate the browser
with temporary cookies, record the visible flow with captions and a synthetic
cursor, and emit MP4, WebM, GIF, and poster derivatives.

## Implementation

Added a JSON storyboard and fixture, isolated server/database lifecycle,
same-origin API seeding, browser capture scenes, visual overlays, media
encoding/validation, and focused fixture tests. The harness applies the
repository's actual Alembic upgrade functions through a synchronous disposable
SQLite connection so the showcase remains usable when aiosqlite cannot open a
worker connection in the host runtime. No product code or normal user data is
modified.

## Verification

`api/.venv/bin/pytest -q portfolio-showcase/tests` passed (4 tests).
`api/.venv/bin/ruff check portfolio-showcase/src portfolio-showcase/tests`
passed. The escalated disposable end-to-end dry run passed, and the full
encoding run produced valid MP4, WebM, GIF, and poster outputs. The generated
GIF was 19.8 MiB and the video viewport was 1280×800.

## Follow-up

Customize `config/storyboard.json` and the fictional fixture when the
portfolio narrative or product UI changes; run `--dry-run` before encoding.
