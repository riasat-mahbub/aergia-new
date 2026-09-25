---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M3B0ZB65S3NPM0AHSQ2QTK8Z
TYPE: feature
STATUS: PROPOSED
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
RELATIONS:
  related:
  - FEAT-01M3A94Y3G98ACN0BK8P9VF305
AFFECTS:
  files:
  - api/app/services/tailoring.py
  - api/app/http_schemas/tailoring.py
  - api/app/services/library.py
  - api/app/services/candidate_index.py
  - api/app/services/candidate_evidence.py
  - api/app/services/tailoring_opportunities.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - web/src/features/tailoring/types/index.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-25T00:55:46.629081+00:00'
UPDATED_AT: '2026-09-25T00:55:46.629081+00:00'
---

# Full-history tailoring dossier and protocol simplification

## Background

Replace semantic retrieval and structured editorial review with a complete plaintext candidate dossier, creation/editing workflow, and canonical preview-to-submit binding.

## Investigation

The local substantial Library has 21 rows and yields a readable full-history
dossier of about 9.1k characters. Completed v8 sessions recorded composition
context responses of about 191k characters and semantic refreshes of about
10 and 90 seconds. The index has no independent product reader beyond the
tailoring path; Library writes maintain it. Backend validation, rendering,
scanner evaluation, and evaluation/hash binding remain necessary.

## Decision

Use an immutable full-history dossier in the active tailoring context. Create
from the job and dossier, preview, edit from PDF/scanner feedback, and let the
agent select any evaluated candidate within the operational preview cap.
Remove the semantic refresh/retrieval and structured editorial-review stages.
Preview returns its normalized candidate so submission can reuse the exact
document whose hash was evaluated. Preserve historical draft review and
backend correctness checks.

## Implementation


## Verification


## Follow-up
