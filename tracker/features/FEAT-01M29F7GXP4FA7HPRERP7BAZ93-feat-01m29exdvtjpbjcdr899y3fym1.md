---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M29F7GXP4FA7HPRERP7BAZ93
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
  - FEAT-01M29EXDVTJPBJCDR899Y3FYM1
AFFECTS:
  files:
  - api/app/services/tailoring.py
  - api/tests/test_tailoring_contracts.py
  - web/src/features/applications/components/detail/GeneratedCvPanel.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-12T00:10:44.022529+00:00'
UPDATED_AT: '2026-09-12T00:10:44.022529+00:00'
---

# FEAT-01M29EXDVTJPBJCDR899Y3FYM1

## Background

Prevented session overlap from hiding owner review: a draft-ready session remains active regardless of agent expiry, backend session creation rejects another run until review/cancel, and the application UI disables starting a second session.

## Investigation

The persistent latest-session UI displays only one session per application.
Allowing a second run before the first draft was reviewed could hide the
earlier draft from the application page while it still occupied CV quota.
Agent credentials expire independently from user review.

## Decision

Allow at most one created, exchanged, or draft-ready tailoring session per
application at a time. The owner can clear the slot by cancelling an active
agent session, or accepting/rejecting its draft. Expiring the agent capability
does not expire a ready draft.

## Implementation

Backend session creation now rejects overlaps and marks expired active
capabilities before creating a replacement. The application panel disables
the start action while the current session is active or awaiting review. Added
contract coverage for draft-ready state after capability expiry and the
overlap guard.

## Verification

Focused API contracts pass; web typecheck and lint pass (with nine existing
React Hook dependency warnings elsewhere in the application).

## Follow-up
