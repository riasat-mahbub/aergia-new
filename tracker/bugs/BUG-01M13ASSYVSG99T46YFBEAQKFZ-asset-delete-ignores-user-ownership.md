---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M13ASSYVSG99T46YFBEAQKFZ
TYPE: bug
STATUS: PLANNED
PRIORITY: High
SEVERITY: High
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS:
- security
- assets
- idor
RELATIONS: null
AFFECTS: null
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-28T04:42:11.803158+00:00'
UPDATED_AT: '2026-08-28T04:42:11.803158+00:00'
---

# asset-delete-ignores-user-ownership

## Background

DELETE /api/v1/assets/{filename} calls PhotoService.delete without user scope; known filenames can be deleted across users and path containment is not enforced. Remediation plan: docs/plans/2026-08-28-security-hardening-and-credential-remediation.md, Task 3.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
