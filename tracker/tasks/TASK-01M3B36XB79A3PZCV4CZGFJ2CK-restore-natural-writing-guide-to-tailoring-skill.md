---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M3B36XB79A3PZCV4CZGFJ2CK
TYPE: task
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - FEAT-01M3B2RC3PNM26Q853X2JYTZWV
AFFECTS:
  files:
  - tailoring-skill/skills/aergia-tailor/references/natural-writing.md
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/AGENTS.md
  - scripts/smoke.sh
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-25T01:34:51.751778+00:00'
UPDATED_AT: '2026-09-25T01:34:51.751778+00:00'
---

# Restore natural writing guide to tailoring skill

## Background

Restore the original candidate-facing prose guide, route the v9 skill to it, and include it in the downloadable bundle.

## Investigation

Protocol v9 removed the writing reference along with schema and review files.
The bundle builder already includes files under the skill's references directory,
but the smoke script explicitly rejected that directory.

## Decision

Restore the original guide unchanged and route the skill to it for drafting and
editing. Keep the v9 session and validation protocol as implemented.

## Implementation

Restored the guide, linked it from SKILL.md, documented it in the local guide,
and changed the smoke bundle assertion to require the file.

## Verification

The restored file's SHA-256 matches the version before the v9 merge. The diff
has no whitespace errors. No test command was run for this documentation change.

## Follow-up
