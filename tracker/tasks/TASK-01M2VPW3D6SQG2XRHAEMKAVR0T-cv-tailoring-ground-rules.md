---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M2VPW3D6SQG2XRHAEMKAVR0T
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - FEAT-01M29BGP4579KM0SJF6PCMH94G
  - TASK-01M2CACAKGPQBC12GX22D5PCHQ
AFFECTS:
  files:
  - tailoring-skill/skills/aergia-tailor/SKILL.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-19T02:10:38.118802+00:00'
UPDATED_AT: '2026-09-19T02:10:38.118802+00:00'
---

# CV tailoring ground rules

## Background

Add approved truth, inference, reorganization, evidence, link, visual, template, readability, page-count, ATS, provenance, exception, and conflict-priority rules to the portable Aergia tailoring skill.

## Investigation

The portable skill already required evidence-backed claims, preserved useful
links, and role-dependent page review, but those decisions were distributed
through the composition and critique instructions rather than stated as one
policy. The approved ground rules add explicit guidance for reasonable
inference, decomposition, visual defaults, template choice, readability,
semantic clarity, exception notes, and conflicts between objectives.

## Decision

Keep the protocol, schemas, renderer, and server-owned identity behavior
unchanged. Add the ground rules as a provider-neutral policy section in the
portable skill. Treat user-confirmed inferences as durable across sessions only
when they reappear in authoritative supplied context.

## Implementation

Added the approved 16-rule `CV tailoring ground rules` section and core
principle to `tailoring-skill/skills/aergia-tailor/SKILL.md`.

## Verification

`git diff --check` passed. `node --test tailoring-skill/tests/*.test.mjs`
passed all three test files.

## Follow-up

None.
