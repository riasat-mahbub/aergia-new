---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M8B37ZQ4TJHY7G8T2TG2RH78
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: High
TAGS:
- development
- portability
- smoke
RELATIONS:
  related:
  - BUG-01M2TQ3SRB02SEVA6NE7XY1T4X
  - BUG-01M2GG5KNVDMZ069PDNB5PNNXM
  - TASK-01M1SM89VRWW75DG1JMXZNDAKQ
AFFECTS:
  files:
  - dev.py
  - api/README.md
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T05:01:24.292343+00:00'
UPDATED_AT: '2026-11-26T05:11:54.337047+00:00'
---

# Add a portable Python development launcher

## Background

Provide Python commands for local Aergia development and the isolated smoke gate on Windows and POSIX systems.

## Implementation

Added `dev.py` with the ordinary Vite launch, `--build`, `--prod`, and `--smoke`. It uses the native virtual environment, reads root dotenv values, runs migrations, and waits for API readiness. The smoke mode checks the built same-origin frontend, security headers, tailoring skill archive, and session cookies with disposable SQLite and upload paths.

## Verification

The full Python smoke gate passed on Windows and Linux under WSL with Ruff 0.12.12. A prepared Windows environment exercised development, build, and production-like serving modes with disposable databases, same-origin API requests, reload selection, and sibling cleanup after a server exit. An interactive Ctrl+C released both development ports.

A Windows run also exercised the real dependency and Chromium installation before starting services. The frontend homepage, API readiness, and same-origin registration configuration each returned HTTP 200. The launcher prints the dependency and browser setup phases before starting the servers.
