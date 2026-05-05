---
ID:             006
TYPE:           issue
NAME:           TEMPLATE_GUIDE.md needs rewrite for manifest format
SUMMARY:        TEMPLATE_GUIDE.md describes the old layout_template pipeline, not the manifest-driven system
STATUS:         OPEN
TAGS:           docs, template-guide
LINKS:          phase=PLAN.md-5.7
---

## Description

The current `TEMPLATE_GUIDE.md` was written for the old user template
system (HTML-only templates with `{{zone_id}}` placeholders). The
manifest-driven pipeline has replaced this, but the guide hasn't been
updated. It references deprecated concepts:
- `layout_template` instead of manifest
- Zone configuration at upload time (now handled by the visual wizard)
- Old customization panel behavior

## What It Should Cover

- Manifest JSON schema reference
- Visual wizard flow (Step 1-4)
- Generated HTML/CSS from manifest
- Asset loading
