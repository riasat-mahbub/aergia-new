---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M0WXYF53Z8PDKRSEVZ8E6JFH
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: riasat
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01M0WXXZ70MYPF5QE4A5ZZG5JN
AFFECTS: null
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-25T17:02:06.499285+00:00'
UPDATED_AT: '2026-08-25T17:02:06.499285+00:00'
---

# BUG-01M0WXXZ70MYPF5QE4A5ZZG5JN

## Background

Dropped the sec_-prefix guard in SectionZoneView.handleDragEnd, switched the parser to emit sec_<hex> ids via _new_id() (no per-type tag), and ran a one-shot data migration that rewrote 149 ids across 7 imported CVs in the dev DB. End-to-end verified: drag-drop on imported CVs now lands in the zone. 101 parser tests pass; 353/357 backend tests pass (4 pre-existing failures unrelated).

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
