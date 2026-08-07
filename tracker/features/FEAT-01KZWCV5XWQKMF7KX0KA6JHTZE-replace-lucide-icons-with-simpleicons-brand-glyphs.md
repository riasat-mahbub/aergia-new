---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KZWCV5XWQKMF7KX0KA6JHTZE
TYPE: feature
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: riasat
CONFIDENCE: High
TAGS:
- renderer
- icons
- legacy-look
RELATIONS: null
AFFECTS:
  files:
    - api/app/services/renderer/html.py
    - api/tests/test_html_renderer.py
LINKS:
  plan: local://legacy-look-preservation-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-13T02:00:00+00:00'
UPDATED_AT: '2026-08-13T02:00:00+00:00'
---

# Replace lucide icons with simpleicons brand glyphs

## Background

The renderer's `_SOCIAL_ICONS` dict used lucide-style stroke outlines (`fill="none" stroke="currentColor"`) for every brand mark. These were hand-drawn approximations, not the real brand glyphs. The user wanted simpleicons brand paths instead — recognizable filled marks that read clearly at small sizes.

## Investigation

Compared legacy `section_renderers/profile.py` (commit 97d55fe) — it shipped the same set of brands via `_SOCIAL_ICON_SVG` but with simpleicons paths fetched at implementation time. The current dict kept the lucide approximation. Fetched official simpleicons paths from `cdn.jsdelivr.net/npm/simple-icons@latest/icons/{slug}.svg` for each brand.

## Decision

Replace all brand glyphs with the official simpleicons filled paths (CC0). Keep utility icons (`globe`/`mail`/`phone`/`link`) as lucide-style outlines since simpleicons does not host those. `x` and `twitter` share the same path because Twitter was rebranded to X.

## Implementation

- `api/app/services/renderer/html.py`: rewrote the `_SOCIAL_ICONS` dict with filled brand paths (github, linkedin, x, twitter, instagram, facebook, youtube, mastodon, medium, stackoverflow, behance, dribbble, gitlab) and kept lucide-style paths for utility icons.
- `api/tests/test_html_renderer.py`: `test_social_field_with_unknown_icon_renders_text_only` previously used `icon="mastodon"` which used to be an unknown key. Now that mastodon is in `_SOCIAL_ICONS`, the test was updated to use `icon="nonexistent-icon-key"` to preserve its actual semantic intent.

## Verification

- Pytest: `tests/test_html_renderer.py` and `tests/test_resolve.py` — 43 passed, 0 failed.
- Rendered HTML inspection (`/tmp/current_modern.html`):
  - Profile social block: 2 `<svg viewBox="0 0 24 24" fill="currentColor">` entries (GitHub + LinkedIn), 0 stroked.
- Visual: brand glyphs render at 0.9em size in the centered profile sidebar; `currentColor` honors the section's accent cascade.

## Follow-up

None. Step 3 of `local://legacy-look-preservation-plan.md` is closed.
