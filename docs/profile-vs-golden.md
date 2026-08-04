# Profile section: current vs golden (/home/riasat/Downloads/CV.pdf)

## Golden (CV.pdf, top of page 1)

| Line | y | size | content |
|---|---|---|---|
| Name | 30.0 | **15.0pt** | "Riasat Mahbub" (centered around x=265) |
| Contact 1 | 50.0 | 9.0pt | `riasat1998@gmail.com · +1 782 409 4525 · Halifax, Nova Scotia` (one line, center, `·` separator) |
| Contact 2 | 64.0 | 9.0pt | `riasat-mahbub Riasat Mahbub rmahbub.com` (3 socials as plain text, one line, center) |
| (Experience heading at y=88) | | | |

## Current renderer (generic-minimal, minimal spacing)

| Line | y | size | content |
|---|---|---|---|
| Name | 30.0 | **18.0pt** | "Riasat Mahbub" (centered around x=258) |
| Title | 52.0 | 10.5pt | "Software Engineer" (one field, centered) |
| Contact | 66.0 | 9.0pt | `riasat@example.com +1 555 0100 Toronto, Canada riasat.dev` (one line, center, **space separator**) |
| Social | 80.0 | 12.0pt | `github linkedin` (icons + text, centered) |
| Summary | 96.0 | 10.5pt | "Software engineer with experience in..." |

## Differences

| Aspect | Golden | Current | Status |
|---|---|---|---|
| **Name font size** | 15.0pt | 18.0pt | **Current is 3pt too big** (regression — pre-existing uncommitted `f-name: 1.25rem` was 15pt, but commit `c77d4a0` shipped `1.5rem`) |
| Title (subtitle) | absent (golden has no "Software Engineer" line under the name) | present (10.5pt centered) | Extra line in current; golden's title likely not set in the data, or is rendered differently |
| **Contact separator** | `·` (middle dot, U+00B7) | space (` `) | Golden uses bullet separators; current concatenates with no separator |
| **Social icon vs text** | Plain text only (`riasat-mahbub Riasat Mahbub rmahbub.com`) | Icon + text (`f-icon` SVG + label) | Golden predates icon support; current uses the icon table |
| **Contact vs social row split** | email+phone+location on row 1; 3 socials on row 2 | email+phone+location+site on row 1; 2 socials on row 2 (separate) | Different field grouping; current's `site` field lands on the contact row in current data |
| **Summary position** | not in profile (may be elsewhere or absent) | in profile (10.5pt) | Current emits summary in profile; golden's data may not have it set, or it's elsewhere |
| **Layout alignment** | Centered (justify-content:center on each row) | Centered (matches) | Same — both centered |
| **Per-field gap** | unknown (golden is PDF text, no CSS) | 0px (just dropped) | Current is very tight |

## Root cause for the 3pt name size regression

`api/app/services/renderer/html.py` line 442 (CSS block):

```css
.f-name { font-size: 1.5rem; font-weight: 700; }
```

`1.5rem` at Chromium's default 16px base = 24px = 18pt.

The pre-existing uncommitted state (before this conversation's git reset) had `1.25rem` = 20px = 15pt, matching the golden. That change was part of the prior typography work that got rolled back.

**Fix**: change `1.5rem` to `1.25rem` in `html.py:442`.

## Other potential fixes (if the user wants the golden look)

- **Centered `·` separator between contact fields**: needs a profile-level "contact row" emitter that uses `·` as a separator. Currently each contact field is its own `<div>` in a flex row, no separator.
- **Drop the title line in profile**: handled by data (just don't set `title` in the profile JSON).
- **Plain-text socials (no icons)**: would need a profile-level flag or a `social_links` rendering mode that skips `f-icon`.
- **Drop the summary from profile**: handled by data (just don't set `summary`).
- **Group site+socials on a single row**: would need a profile-level emitter that puts site+socials on one row instead of two.

## What this is NOT

- The current is not "broken" — it has the user's profile data, the typography is consistent, and the layout is centered. The differences from the golden are stylistic choices, with one genuine regression (name size 3pt too big).
- The user has not asked for the profile to look exactly like the golden. The comparison is informational — let them decide what to fix.
