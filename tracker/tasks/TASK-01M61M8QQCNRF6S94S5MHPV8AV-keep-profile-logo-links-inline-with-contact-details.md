---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M61M8QQCNRF6S94S5MHPV8AV
TYPE: task
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS:
  files:
  - api/app/services/renderer/builders/profile.py
  - api/app/services/renderer/html_renderer/html_document.py
  - api/tests/test_builders.py
  - api/tests/test_html_renderer.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-10-28T16:07:38.476412+00:00'
UPDATED_AT: '2026-10-28T16:07:38.476412+00:00'
---

# Keep profile logo links inline with contact details

## Background

Group social logo links with email, phone, location and website in the profile contact row. Preserve natural wrapping, clickable destinations and custom styles. Add a small gap before the first logo; update existing builder expectations and the renderer HTML fingerprint. Verified 118 focused renderer/profile/link tests and Chromium desktop and narrow fixtures for all three templates.

## Investigation


## Decision


## Implementation


## Verification

118 focused renderer, builder, profile URL and link tests passed. Chromium
fixtures confirmed a shared contact row in all three templates at 794px and
360px, with natural wrapping in narrow containers. Visually checked Classic
desktop and Minimal narrow screenshots. The design detector reported no
findings. `./dev.sh --smoke` passed.

## Follow-up
