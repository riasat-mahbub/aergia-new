---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KZKSF0A0R2P7AE3YKBZPC052
TYPE: bug
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01KZKSERP6P868SCQMXGE2QMWQ
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T17:34:53.761085+00:00'
UPDATED_AT: '2026-08-09T17:34:53.761085+00:00'
---

# BUG-01KZKSERP6P868SCQMXGE2QMWQ

## Background

Fixed: pdf.py and cvs.py preview_cv now call build_document(cv, manifest_model) instead of (cv, None), so manifest policy_overrides apply in the PDF and the server preview exactly as in the live preview. Verified: switched CV PDF renders the new template's serif stack. Tests: test_build_document_applies_manifest_policy_overrides, test_build_document_without_manifest_uses_type_default.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
