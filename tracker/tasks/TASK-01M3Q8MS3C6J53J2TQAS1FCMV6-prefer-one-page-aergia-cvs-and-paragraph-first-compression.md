---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M3Q8MS3C6J53J2TQAS1FCMV6
TYPE: task
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
RELATIONS:
  related:
  - TASK-01M3B909J1D92M5B35VE8ZJGJR
AFFECTS:
  files:
  - tailoring-skill/AGENTS.md
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/references/cv-guidelines.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-29T19:00:42.220802+00:00'
UPDATED_AT: '2026-09-29T19:00:42.220802+00:00'
---

# Prefer one-page Aergia CVs and paragraph-first compression

## Background

Update the portable and installed tailoring skill to prefer a readable one-page CV and convert related bullets into paragraphs before cutting supported content.

## Investigation

The portable skill and writing reference treated page count as a tie-breaker
after numeric job fit. Both used bullets as the default description shape,
which encouraged cutting content before trying paragraph flow.

## Decision

Prefer one readable page while retaining the strongest required job-fit
evidence and reliable PDF parsing. Use bullets for distinct points, and try
concise paragraphs before cutting content when space is tight. Two pages
remain appropriate when a one-page version would materially weaken the CV.

## Implementation

Updated the portable skill's drafting, overflow, and preview-selection
guidance, its optional CV writing reference, and the subtree guide. Applied
the same new guidance to the installed skill without replacing its other
installed instructions.

## Verification

Both the portable and installed skills passed `quick_validate.py`; `cmp`
confirmed the installed file matches the staged edit. `git diff --check`
passed. `tracker rebuild` and `tracker validate` completed with 0 errors and
7 existing fork warnings. No tests were run for this documentation-only change.

## Follow-up

None.
