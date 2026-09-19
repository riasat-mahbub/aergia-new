---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M2X6W530N921G9STWMCNC12J
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
  - TASK-01M2VPW3D6SQG2XRHAEMKAVR0T
AFFECTS:
  files:
  - api/app/document_schema/capabilities.py
  - api/app/services/tailoring.py
  - api/tests/test_tailoring_contracts.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-19T16:09:31.488602+00:00'
UPDATED_AT: '2026-09-19T16:09:31.488602+00:00'
---

# Allow tailoring agent to edit profile location

## Background

Remove profile location from the backend server-owned field policy and preserve agent-tailored location during candidate normalization, while retaining protection for other identity fields.

## Investigation

The capability descriptor listed `profile.location` as server-owned, and
`TailoringService._inject_profile_identity` replaced the candidate's location
with the stored profile value during both preview and submit normalization.
This contradicted the tailoring ground rule that permits adapting street-level
location disclosure for a job.

## Decision

Make only `profile.location` candidate-editable. Keep the stored profile
unchanged, and continue reinjecting the remaining server-owned identity and
contact fields. The candidate remains an unlinked draft for user review.

## Implementation

Removed `location` from `SERVER_OWNED_PROFILE_FIELDS` and from server-side
identity injection. Updated the normalization comment and added assertions
that the capability reports location as editable and a tailored location
survives normalization while other protected fields are still injected.

## Verification

`./.venv/bin/pytest --noconftest -q tests/test_tailoring_contracts.py` passed
all 8 tests. Ruff and `git diff --check` passed. The normal pytest invocation
was interrupted because the global test conftest runs Alembic migrations
during startup in this environment.

## Follow-up

None.
