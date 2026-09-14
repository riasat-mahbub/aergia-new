---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2CA92Q3DZB12DH266Y5ZMPT
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M2C8BECV7TMNBM5A51PWG96A
AFFECTS:
  files:
  - tailoring-skill/skills/aergia-tailor/SKILL.md
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-13T02:41:55.427819+00:00'
UPDATED_AT: '2026-09-13T02:41:55.427819+00:00'
---

# FEAT-01M2C8BECV7TMNBM5A51PWG96A

## Background

Tailoring instructions now preserve and present supported experience with balanced, concise bullet groups.

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
