---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KZWCJY2HK9WZWXE8SM7K5N3H
TYPE: feature
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: riasat
CONFIDENCE: High
TAGS:
- renderer
- tokens
- legacy-look
RELATIONS: null
AFFECTS:
  files:
    - api/app/services/renderer/tokens.py
    - api/app/schema/models.py
    - api/app/db/seed.py
    - api/tests/test_resolve.py
LINKS:
  plan: local://legacy-look-preservation-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-13T01:50:00+00:00'
UPDATED_AT: '2026-08-13T01:50:00+00:00'
---

# Restore legacy spacing and padding values

## Background

The legacy seed (commit 97d55fe) declared spacing and padding values directly: `section_gap=20px`, `subsection_gap=12px` for Classic; `section_gap=16px`, `subsection_gap=8px` for Minimal; `padding=32px` for both single-column templates. The current AST pipeline re-encoded these into a closed token vocabulary but the token values drifted — `compact` mapped to `16px/12px` instead of `20px/12px`, `minimal` mapped to `8px/8px` instead of `16px/8px`, and `comfortable` (24px) covered both Modern's section gap and Classic/Minimal's 32px padding need.

## Investigation

Compared legacy seed (`git show 97d55fe:api/app/db/seed.py`) against current seed. Identified the drift in `tokens.py:SPACING_TOKEN_VALUES` and the absence of a 32px-only padding token (current `loose` already maps to 32px but is semantically a "loose" preset, not a "spacious" preset).

## Decision

Widen `compact` and `minimal` spacing values to match legacy ratios; add a new `spacious` padding token (32px) and route Classic + Minimal seeds through it. Keep `loose` mapping (32px) for backward compatibility. No new schema literal beyond extending `SpacingToken` in both `models.py` and `tokens.py`.

## Implementation

- `api/app/services/renderer/tokens.py`: `compact` → `("20px", "12px")`, `minimal` → `("16px", "8px")`. Added `"spacious": "32px"` to `PADDING_TOKEN_VALUES`; extended `PaddingToken` literal to include `"spacious"`.
- `api/app/schema/models.py`: extended `SpacingToken` literal to include `"spacious"` (line 50).
- `api/app/db/seed.py`: Classic and Minimal seeds' `main` zone `padding` switched from `comfortable`/`loose` to `spacious`. Modern unchanged.
- `api/tests/test_resolve.py`: three test assertions updated from old values to new (compact→20px, minimal→16px, user-customizations→20px).

## Verification

- Pytest: `tests/test_html_renderer.py` and `tests/test_resolve.py` — 43 passed, 0 failed.
- Rendered HTML inspection (`/tmp/current_*.html`):
  - Classic: `--spacing-section: 20px`, `--spacing-subsection: 12px`, zone `padding:32px`.
  - Minimal: `--spacing-section: 16px`, `--spacing-subsection: 8px`, zone `padding:32px`.
  - Modern: zone `padding:24px` (unchanged).

## Follow-up

None. Step 2 of `local://legacy-look-preservation-plan.md` is closed.
