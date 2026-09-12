---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M29TDET7S9FZ7YFFCN43YV8S
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: High
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
- sqlite
RELATIONS:
  related:
  - FEAT-01M29F7GXP4FA7HPRERP7BAZ93
AFFECTS:
  files:
  - api/app/services/tailoring.py
  - api/tests/test_tailoring.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-12T03:26:12.807495+00:00'
UPDATED_AT: '2026-09-12T03:26:12.807495+00:00'
---

# Tailoring submit expires application after quota reservation

## Background

Protocol-v2 candidate preview succeeds, but submit returns HTTP 500 because SQLite quota reservation rolls back the context read transaction and expires the loaded Application before its ID is serialized. Capture the application ID before quota reservation and cover the full create, exchange, context, submit, and unlinked-draft flow.

## Investigation

The capability-scoped preview rendered successfully, but submission returned
HTTP 500. The transaction rolled back completely: the session remained
``exchanged`` with no draft and zero attempts. ``QuotaService.reserve`` starts
the SQLite write transaction by rolling back any active read transaction,
which expires ORM objects loaded while building the tailoring context.
``TailoringService.submit`` then accessed ``application.id`` after that reset.

## Decision

Capture immutable identifiers needed by the result before reserving quota.
Keep draft creation transactional and keep the application CV link unchanged
until owner review.

## Implementation

Captured ``application_id`` before ``CVService.create_cv`` reserves quota and
used the scalar in the stored result and response. Added an HTTP regression
covering session creation, exchange, context retrieval, candidate submission,
and the unlinked review draft contract.

## Verification

Compileall and Ruff pass for the backend and regression test. The live failed
request was confirmed fully rolled back. The focused pytest command remains
blocked before collection by the repository's documented Python
3.14/aiosqlite Alembic startup hang.

## Follow-up
