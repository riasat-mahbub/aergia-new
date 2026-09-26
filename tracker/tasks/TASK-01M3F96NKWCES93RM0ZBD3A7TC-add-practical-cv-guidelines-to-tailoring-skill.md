---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M3F96NKWCES93RM0ZBD3A7TC
TYPE: task
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
RELATIONS: null
AFFECTS:
  files:
  - tailoring-skill/skills/aergia-tailor/references/cv-guidelines.md
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/AGENTS.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-26T16:36:33.020431+00:00'
UPDATED_AT: '2026-09-26T16:36:33.020431+00:00'
---

# Add practical CV guidelines to tailoring skill

## Background

Add a separate CV writing and presentation reference, routed from the drafting workflow, using supported Aergia controls and qualified ATS advice.

## Investigation

The current frontend AlignmentGroup excludes profile, but the document schema
and renderer support profile subsection.text_align. Historical tracker entries
describe profile alignment in the older CustomizePanel. Font consistency can
be maintained through existing section typography. Page setup remains owned
by the template/renderer rather than section spacing controls. The skill bundle
already collects reference files recursively.

## Decision

Keep generic resume advice in a separate reference with capability-aware
instructions. Treat metric counts, font examples, and margin ranges as
preferences rather than universal ATS pass/fail rules.

## Implementation

Added cv-guidelines.md covering contact details, headings, title matching,
dates, education, summaries, seniority, achievements, links, density,
typography, alignment, reading order, margins, paper, and export. Linked it
from Pass 1 and instructed agents to reapply it during preview revisions.
Documented the reference in the subtree guide. Protocol and controls unchanged.

## Verification

Reviewed the reference against the current customization, schema, renderer,
and bundle source. No application tests run for this documentation change.

## Follow-up

Profile alignment remains supported in candidate styles but hidden by the
current frontend AlignmentGroup; changing that UI is outside this task.
