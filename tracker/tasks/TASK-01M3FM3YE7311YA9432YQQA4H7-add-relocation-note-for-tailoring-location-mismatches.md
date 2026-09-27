---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M3FM3YE7311YA9432YQQA4H7
TYPE: task
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
RELATIONS:
  related:
  - TASK-01M2X6W530N921G9STWMCNC12J
AFFECTS:
  files:
  - tailoring-skill/skills/aergia-tailor/SKILL.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-26T19:47:18.087176+00:00'
UPDATED_AT: '2026-09-26T19:47:18.087176+00:00'
---

# Add relocation note for tailoring location mismatches

## Background

Append (Open to relocation) to the tailored candidate location when the job requires a different location, preserving the actual location and stored profile.

## Investigation

Tailored candidate location is already editable; no API or schema change is needed.

## Decision

Keep the current location and append the exact relocation note for a clear
job-location mismatch. Respect explicit user instructions against relocation.

## Implementation

Added the rule to Pass 1, including duplicate-note prevention and exceptions
for matching, unspecified, ambiguous, or compatible remote locations. Changes
apply only to the candidate, leaving the stored profile intact.

## Verification

Skill quick validation and `git diff --check` passed. Reviewed the rule for
clear mismatches, matching locations, remote eligibility, missing locations,
existing relocation notes, and explicit user preferences. No runtime code changed.

## Follow-up

None.
