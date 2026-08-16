---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNED
TYPE: task
STATUS: PROPOSED
SUMMARY: Drop is_system and user_id columns from Template; Alembic migration; update
  seed.
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: riasat
CONFIDENCE: High
TAGS:
- phase-6
- migration
RELATIONS:
  part_of:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN9Q
AFFECTS:
  files:
  - api/app/models/template.py
  - api/app/models/user.py
  - api/app/db/seed.py
  - api/alembic/versions/
LINKS:
  plan: local://phase-6-content-only-authoring-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: 2026-08-08
UPDATED_AT: 2026-08-08
---

# Drop is_system and user_id from Template

## Background

After deletion of the user-templates routes, every `Template` row is a system
template. The `is_system: bool` column and the `user_id` FK + index become
vestigial and must be removed for clean cutover.

## Decision

Drop both columns at the model level AND add an Alembic migration that drops
them at the schema level. The migration sets `user_id=NULL` for every row
before dropping (the column is nullable; rows that point at deleted users
should not block the drop). The `is_system` boolean is dropped without
preservation — all rows were system anyway, so the column carried no
information.

The `User.templates` back-reference is dropped (Template no longer has the
`user` relationship). The `User.cvs` relationship stays.

`seed.py` stops passing `is_system=True` to the `Template(...)` constructor.

## Implementation

Plan §4.9 + §4.10. New migration `api/alembic/versions/b1_phase6_content_only_authoring.py`
with `down_revision = 'a0aa74606361'`.

`upgrade()`:
1. `UPDATE templates SET user_id = NULL WHERE user_id IS NOT NULL;`
2. `op.drop_index(op.f('ix_templates_user_id'), table_name='templates')`
3. `op.drop_column('templates', 'user_id')`
4. `op.drop_column('templates', 'is_system')`

`downgrade()` reverses the steps: re-add columns with appropriate types,
re-add the index. The user_id back-population is not attempted (data loss is
acceptable in downgrade; document in migration docstring).

## Verification

```bash
rm -f api/data/aergia.test.db
cd api && alembic upgrade head && pytest -q
# expect: 157 baseline tests pass after migration + new tests
grep -rn "is_system\|user_id" api/app/models/template.py
# expect: zero matches on the Template model itself
```

## Follow-up

None.

<!-- Migrated from TASK-01KZPHASE6STEP1-CLEANUP during the schema-4 cutover. -->
