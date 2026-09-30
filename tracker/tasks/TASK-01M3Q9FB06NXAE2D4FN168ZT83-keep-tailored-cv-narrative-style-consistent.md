---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M3Q9FB06NXAE2D4FN168ZT83
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
  - TASK-01M3Q8MS3C6J53J2TQAS1FCMV6
AFFECTS:
  files:
  - tailoring-skill/AGENTS.md
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/references/cv-guidelines.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-29T19:15:12.518492+00:00'
UPDATED_AT: '2026-09-29T19:15:12.518492+00:00'
---

# Keep tailored CV narrative style consistent

## Background

Add guidance to keep summary and description voice and bullet-versus-paragraph format consistent across comparable CV entries, including when making one-page layout changes.

## Investigation

The new paragraph-first page-fit guidance could leave a CV with bullets in
some comparable entries and paragraphs in others. It also did not explicitly
ask for consistent voice and level of detail across narrative fields.

## Decision

Choose a dominant narrative format across summary and description fields.
Keep bullets or paragraphs consistent among comparable entries, including
when paragraph flow is used to fit one page. Maintain a coherent voice and
tense without making sentence openings formulaic.

## Implementation

Updated the portable skill, its CV writing reference, the subtree guide, and
the installed skill. The installed copy retains its other instructions.

## Verification

Both skill copies passed `quick_validate.py`; the installed copy matched the
staged edit. `git diff --check` passed. No tests were run for this
documentation-only change. `tracker rebuild` and `tracker validate` completed
with 0 errors and the 7 existing fork warnings.

## Follow-up

None.
