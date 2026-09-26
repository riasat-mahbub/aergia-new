---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M3F9MB8QYSZ38J5NBTWAT5A0
TYPE: task
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01M3F96NKWCES93RM0ZBD3A7TC
AFFECTS:
  files:
  - web/src/features/builder/components/customization/groups/LayoutGroups.tsx
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/references/cv-guidelines.md
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-26T16:44:01.176035+00:00'
UPDATED_AT: '2026-09-26T16:44:01.176035+00:00'
---

# Restore Profile alignment and make CV guidelines optional

## Background

Follow-up implementation: expose Profile alignment using existing subsection controls and preserve renderer-backed two-column gating. Route the separate CV guidelines as optional contextual advice while preserving mandatory natural-writing guidance and accuracy constraints.

## Investigation

Profile already uses the normal subsection style and persistence paths, with
Center as its inherited default. The renderer dispatches two-column entries
generically, so its alignment restriction remains applicable. The public skill
bundle collects reference files recursively.

## Decision

Expose existing alignment controls for Profile. Make the new CV guidance
optional and contextual, preserving the original natural-writing instructions
and mandatory factual accuracy constraints.

## Implementation

Removed the Profile visibility guard and unused instance destructuring from
AlignmentGroup. Preserved its existing two-column disabled state. Added an
optional CV-guidelines paragraph in SKILL.md; revised the reference introduction
and preview guidance to remove compulsory use. Implemented by two GPT-6 Luna
agents with integration review by the primary agent.

## Verification

Frontend typecheck passed. Lint passed with zero errors and nine existing hook
dependency warnings. Reviewed the save and renderer style paths in source.
Built the public skill ZIP and confirmed both CV and natural-writing references
are included. git diff --check passed. No browser/PDF runtime check was run.

## Follow-up

Browser interaction and exported PDF behavior were not exercised in this task.
