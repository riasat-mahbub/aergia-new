---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M38HD5CTRGEC23AJNVC5WES9
TYPE: bug
STATUS: IN_PROGRESS
PRIORITY: Medium
SEVERITY: Medium
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
- protocol-v6
RELATIONS:
  related:
  - FEAT-01M38F0X03A98MD7EAZTQGKN4V
AFFECTS:
  files:
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/tests/session.test.mjs
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-24T01:45:13.370398+00:00'
UPDATED_AT: '2026-09-24T01:45:13.370398+00:00'
---

# Isolate tailoring proposition outputs by source

## Background

A multi-source live v6 tailoring session observed a previous source result at the next source stage. The helper now gives each source a distinct hash-suffixed output path and verifies staged files are cleared. Added a two-source regression test; complete the real-world session after the user provides a fresh one-time code.

## Investigation

`tracker search` found no existing item for isolated proposition extraction. The live v6 workflow
reached a later source with the earlier source's proposition result still visible at the shared
`current-propositions.json` path, so the helper rejected the mismatched source ID and exited.

## Decision

Give each source a deterministic, source-specific proposition output path. Validate that both staged
files are removed before advancing to another source.

## Implementation

Changed the helper and staged instructions to use the source-specific path. Extended the session
test to process two sources and leave a stale legacy filename present while the second source is
submitted, proving it cannot be consumed as the active result.

## Verification

`node --test tailoring-skill/tests/*.test.mjs` — 4 test files passed. `git diff --check` passed.

## Follow-up

Resume the interrupted real-world tailoring session after the user supplies a fresh one-time code;
the prior code has been exchanged and cannot be reused.
