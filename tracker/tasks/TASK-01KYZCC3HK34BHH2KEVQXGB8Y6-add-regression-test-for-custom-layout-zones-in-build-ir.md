---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KYZCC3HK34BHH2KEVQXGB8Y6
TYPE: task
STATUS: PLANNED
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- plan
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T19:21:18.643472+00:00'
UPDATED_AT: '2026-08-01T19:21:18.643472+00:00'
---

# Add regression test for custom layout zones in build_ir

## Background

Add regression test api/tests/test_ir_zones.py. Verify: cd api && source .venv/bin/activate && pytest tests/test_ir_zones.py. Expect: new test asserts a custom layout_config.zones with a newly-added zone posted to build_ir returns DocumentIR.rows including that zone. Write test FIRST (TDD) and confirm it FAILS on current code, then apply step 1 and confirm PASSES.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
