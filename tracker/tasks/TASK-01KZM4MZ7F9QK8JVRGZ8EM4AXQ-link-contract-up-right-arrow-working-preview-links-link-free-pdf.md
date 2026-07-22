---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KZM4MZ7F9QK8JVRGZ8EM4AXQ
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T20:50:23.599883+00:00'
UPDATED_AT: '2026-08-09T20:50:23.599883+00:00'
---

# Link contract: up-right arrow, working preview links, link-free PDF

## Background

Post-implementation change to docs/plans/2026-08-09-field-layout-fixes.md. Arrow -> U+2197 up-right diagonal. Preview keeps real hrefs with target=_blank rel=noopener (render.py make_anchors_open_in_new_tab; /render/html preview branch + /cvs/{id}/preview); iframe sandbox gains allow-popups. PDF strips anchors to spans via strip_anchor_markup in _pdf_runtime.html_to_pdf (covers /render/pdf + /cvs/{id}/export/pdf) so Chromium emits no link annotations. Old strip_anchor_hrefs deleted. Tests: tests/test_render_links.py + arrow assertion.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
