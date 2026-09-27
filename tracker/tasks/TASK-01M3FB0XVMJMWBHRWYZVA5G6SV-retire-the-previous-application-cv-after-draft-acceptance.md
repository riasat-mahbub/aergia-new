---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M3FB0XVMJMWBHRWYZVA5G6SV
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
  - api/app/services/tailoring.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-26T17:08:22.004529+00:00'
UPDATED_AT: '2026-09-26T17:08:22.004529+00:00'
---

# Retire the previous application CV after draft acceptance

## Background

After successful draft acceptance, soft-delete the replaced application-owned CV in the same transaction and release its CV quota. Preserve standalone sources and CVs still selected by another application.

## Investigation

accept_draft validates candidate and scanner bindings, then conditionally
switches Application.cv_id. Previously it left the replaced CV active.
CVService.delete_cv already implements soft deletion and quota release;
the route dependency owns commit/rollback for the complete operation.

## Decision

Retire the immediately replaced source only after the current-CV switch
succeeds, and only when the source belongs to the same application and user.
Preserve any source still selected by another application. Keep historical
session references intact through soft deletion.

## Implementation

Added acceptance-only cleanup after the successful compare-and-swap and before
marking the session accepted. The cleanup reuses CVService.delete_cv, so quota
release and deactivation commit or roll back with acceptance. Initial drafts,
rejected drafts, failed acceptance, unrelated CVs, and historical backlog are
not cleaned up by this change.

## Verification

Ruff passed for app/services/tailoring.py; git diff --check passed. Reviewed
transaction ownership, failure ordering, current-CV reference protection, and
the existing deletion/quota implementation. No tests were added or run.

## Follow-up

The existing ownerless CV backlog and application deletion/switching policies
are separate from retirement on future successful draft acceptance.
