---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M2CACAKGPQBC12GX22D5PCHQ
TYPE: task
STATUS: DONE
PRIORITY: Low
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - FEAT-01M2CACX71J8BCZGVJRB6VAS9K
AFFECTS:
  files:
  - tailoring-skill/skills/aergia-tailor/SKILL.md
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-13T02:43:41.808604+00:00'
UPDATED_AT: '2026-09-13T02:43:41.808604+00:00'
---

# Balance peer bullet detail in tailoring skill

## Background

Incorporate user feedback to keep bullet counts similar across comparable CV entries, use multiple distinct points when evidence supports them, and reword/compact before removing supported content.

## Investigation


## Decision


## Implementation

Added composition and critique guidance to the portable tailoring skill:
balance substantive bullet counts across comparable entries, use multiple
distinct points when the evidence supports them, and rephrase/compact before
removing supported content. The critique flags unevenness only when it
underrepresents relevant evidence, without demanding artificial symmetry.


## Verification

`node --test tailoring-skill/tests/*.test.mjs` passed all three test files.
The installed skill was synced with the portable source.


## Follow-up
