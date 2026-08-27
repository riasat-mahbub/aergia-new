---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNEH
TYPE: task
STATUS: PROPOSED
SUMMARY: Adjust resolve.py so a SectionInstance.policy on the AST is not clobbered
  by the type default.
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: riasat
CONFIDENCE: High
TAGS:
- phase-6
- resolver
- policy
RELATIONS:
  part_of:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN9R
AFFECTS:
  files:
  - api/app/services/renderer/resolve.py
  - api/app/services/renderer/builders/__init__.py
  - api/tests/test_resolve.py
  - api/tests/test_builders.py
LINKS:
  plan: local://phase-6-content-only-authoring-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: 2026-08-08
UPDATED_AT: 2026-08-08
---

# Resolver respects per-instance SectionPolicy

## Background

The resolver's `resolve()` function unconditionally overwrites `section.policy` with `resolve_policy(section.type, manifest_model)` at `api/app/services/renderer/resolve.py:320`. This clobbers any per-instance policy the build stage already placed on the section.

## Decision

Change the resolver's policy-application step to honour an existing `section.policy` if present and only fall back to `resolve_policy(type, manifest)` otherwise.

## Implementation

Read `resolve.py:resolve()` around line 320 and replace the unconditional overwrite with the conditional:

```python
if section.policy is None:
    section = section.model_copy(update={"policy": resolve_policy(section.type, manifest_model)})
```

That's it. The build stage already produces sections with the resolved per-instance policy attached; the resolver just needs to not throw it away.

Add tests:

- `api/tests/test_resolve.py::test_resolver_preserves_per_instance_policy` — build two skills instances with different `skill_variant`; assert the resolved model has both values intact.
- `api/tests/test_builders.py::test_build_section_style_uses_instance_policy_over_type_default` — assert `build_section_style` returns the instance policy when present and the type default otherwise.

## Verification

```bash
cd api && pytest -q tests/test_resolve.py tests/test_builders.py
# expect: existing tests + 2 new tests pass
```

## Follow-up

None.

<!-- Migrated from TASK-01KZPHASE6STEP2-RESOLVER during the schema-4 cutover. -->
