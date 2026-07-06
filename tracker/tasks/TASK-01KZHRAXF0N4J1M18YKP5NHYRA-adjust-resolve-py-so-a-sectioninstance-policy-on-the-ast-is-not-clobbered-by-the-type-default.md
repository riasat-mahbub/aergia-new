---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KZHRAXF0N4J1M18YKP5NHYRA
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: riasat
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01KZPHASE6STEP2-RESOLVER
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-08T22:36:42.336644+00:00'
UPDATED_AT: '2026-08-08T22:36:42.336644+00:00'
---

# Adjust resolve.py so a SectionInstance.policy on the AST is not clobbered by the type default.

## Background

Closed 2026-08-08 by Phase 7 closeout. resolve() now respects a section's existing policy and only falls back to resolve_policy(type, manifest) when none is set. Covered by test_resolver_preserves_per_instance_policy.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
