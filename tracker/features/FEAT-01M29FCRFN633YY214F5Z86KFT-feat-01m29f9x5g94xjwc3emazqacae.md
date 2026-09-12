---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M29FCRFN633YY214F5Z86KFT
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M29F9X5G94XJWC3EMAZQACAE
AFFECTS:
  files:
  - api/app/services/tailoring.py
  - api/tests/test_tailoring_contracts.py
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-12T00:13:35.605488+00:00'
UPDATED_AT: '2026-09-12T00:13:35.605488+00:00'
---

# FEAT-01M29F9X5G94XJWC3EMAZQACAE

## Background

Included the application's currently linked CV ID in the context freshness hash, so starting standard generation or otherwise changing the application CV link makes an exchanged tailoring context stale before it can submit.

## Investigation

Acceptance already compared the current application CV to the source CV, but
the exchanged context hash did not include the application's current CV link.
An independent CV generation could therefore leave an agent working from an
outdated context until the final accept conflict.

## Decision

Treat the linked CV ID as part of the application context snapshot, making a
changed link stale before preview/submission.

## Implementation

Added the linked CV ID to the context freshness basis and a contract test that
asserts the snapshot changes when the link changes.

## Verification

Focused API contract tests and Ruff pass.

## Follow-up
