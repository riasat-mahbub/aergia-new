---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M14T0VS9RJP9GFRX0BYDMXP2
TYPE: bug
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS:
- cv
- validation
- api
RELATIONS: null
AFFECTS:
  files:
  - api/app/schemas/cv.py
  - api/tests/test_cvs.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-28T18:27:26.121573+00:00'
UPDATED_AT: '2026-08-28T18:27:26.121573+00:00'
---

# CV customization save validation crash

## Background

Populated CV customizations caused CV creation and update validation to raise a raw TypeError because an outer max_length constraint was applied to the parsed Customizations model.

## Investigation

Pydantic converts a populated customization payload into the typed
`Customizations` model before applying field constraints. The outer
`max_length=100` on the `CVCreate.customizations` and `CVUpdate.customizations`
fields then called `len()` on that model, raising `TypeError` instead of
returning a validation response.

## Decision

Keep collection-size limits on the individual customization dictionaries
(`flags` and `per_section`) and remove the invalid outer length constraint.

## Implementation

Removed `max_length=100` from both CV customization request fields and added
POST/PATCH regression coverage for populated `layout`, `flags`, and
`per_section` values.

## Verification

`ruff check app/schemas/cv.py tests/test_cvs.py` passed. Direct Pydantic
validation passed for both `CVCreate` and `CVUpdate` with all three populated
customization branches. The endpoint test run was attempted but its fixture
blocked during `aiosqlite` connection/migration setup in the environment.

## Follow-up
