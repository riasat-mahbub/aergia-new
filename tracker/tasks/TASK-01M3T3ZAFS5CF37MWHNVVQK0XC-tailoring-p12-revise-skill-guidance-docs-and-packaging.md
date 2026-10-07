---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M3T3ZAFS5CF37MWHNVVQK0XC
TYPE: task
STATUS: PLANNED
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
- v10
- implementation-plan
RELATIONS:
  depends_on:
  - TASK-01M3T3Z9HZNMHFY5Z02XR2BV9P
AFFECTS:
  files:
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/AGENTS.md
  - tailoring-skill/README.md
  - docs/matching-and-tailoring.md
  - api/tests/test_skill_identity.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-30T21:36:48.121260+00:00'
UPDATED_AT: '2026-09-30T21:36:48.121260+00:00'
---

# Tailoring P12 revise skill guidance docs and packaging

## Background

Planned only. Implement P12 from docs/plans/2026-09-30-tailoring-v10-execution-packets.md, following the frozen contract in docs/plans/2026-09-30-tailoring-v10-implementation.md. Execution will use gpt-6-luna with max reasoning later; no implementation or agents started during planning.

## Investigation

Derived from audit T01–T12 and the subsequent ideal-CV, inference, and
independent-PDF-review discussion. See the
[implementation plan](../../docs/plans/2026-09-30-tailoring-v10-implementation.md)
and [execution packets](../../docs/plans/2026-09-30-tailoring-v10-execution-packets.md).

## Decision

Keep the blind ideal-CV stage, enable reasonable inference, retain advisory
owner judgment, and bind review to the actual canonical PDF. Execution uses
gpt-6-luna with max reasoning later, under coordinator-managed file ownership.

## Implementation

Pending packet P12. Parent feature: FEAT-01M3T3Z9FBY8M2EAXQVC5AZMZP.
The linked packet defines owned files, dependencies, focused verification,
and acceptance conditions. Do not broaden scope or change frozen contracts
without coordinator review.

## Verification

Planning only. Runtime checks and semantic PDF inspection are specified in
the plan and have not been executed for this implementation work.

## Follow-up
P00 enables prose work; completion also requires P08/P07 integration before final packaging verification.
Do not mark this entry DONE until its acceptance evidence exists.
