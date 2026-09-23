---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M3601DS116YA29Z5FRTJ2REY
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
RELATIONS:
  related:
  - TASK-01M2VPW3D6SQG2XRHAEMKAVR0T
  - FEAT-01M29BGP4579KM0SJF6PCMH94G
AFFECTS:
  files:
  - api/app/http_schemas/tailoring_evaluation.py
  - api/tests/test_tailoring.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/references/cv-composition.md
  - tailoring-skill/skills/aergia-tailor/references/editorial-review.schema.json
  - tailoring-skill/skills/aergia-tailor/references/evidence-and-inference.md
  - tailoring-skill/skills/aergia-tailor/references/natural-writing.md
  - tailoring-skill/skills/aergia-tailor/scripts/validate-editorial-review.mjs
  - tailoring-skill/tests/editorial-review.test.mjs
  - web/src/features/tailoring/types/index.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-23T02:03:14.081537+00:00'
UPDATED_AT: '2026-09-23T02:03:14.081537+00:00'
---

# Tailoring evidence-first reconstruction guidance

## Background

Consolidate CV evidence decomposition, target prioritization, reconstruction, composition, evaluation, and editorial review guidance into the portable skill; add targeting review category across schema and runtime contracts.

## Investigation

The skill already encouraged re-authoring, but its target strategy still mapped 5–10 themes to CV
locations, and separate evidence/composition references repeated editorial rules. This left the
workflow anchored to source entries and allowed requirement coverage and accent color to compete
with relevance-first composition.

## Decision

Make `SKILL.md` the sole authority for CV evidence and composition behavior. Decompose source
material into atoms before targeting, select 3–6 role priorities, rank evidence by target relevance
and confidence separately, then reconstruct entries and check for source inertia. Keep writing
guidance and versioned schemas separate. Extend the `targeting` finding category through the schema,
validators, API model, and frontend type without changing the protocol version.

## Implementation

Rewrote the strategy and composition guidance, added bounded professional-practice inference and
relevance-first abstraction, anchored target capabilities in body entries, restored reverse
chronology and the monochrome visual default, and added score-regression diagnostics. Removed the
now-redundant evidence and composition references. Updated the editorial review schema and all
runtime category contracts; adjusted bundle and category tests.

## Verification

`node --test tailoring-skill/tests/*.test.mjs` passed (3 tests).
`api/.venv/bin/pytest -q tests/test_tailoring.py` passed (4 tests).
`web npm run typecheck` passed. `web npm run lint` passed with 9 existing hook dependency warnings
in unrelated builder/rich-text files. `git diff --check` passed.

## Follow-up

None.
