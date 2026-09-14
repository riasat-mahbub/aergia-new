---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2B5K5QSDA8BDVRRAATRQ4NW
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M2B44PJKMGCDCTDC13K3Q3JB
  depends_on:
  - ADR-01M2B5K5731EAMMSGCAKWQ3J2V
  related:
  - FEAT-01M29EXDVTJPBJCDR899Y3FYM1
AFFECTS:
  files:
  - api/app/http_schemas/tailoring.py
  - api/app/services/quality.py
  - api/app/services/tailoring.py
  - api/tests/test_quality.py
  - api/tests/test_tailoring.py
  - api/tests/test_tailoring_contracts.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/references/critique.schema.json
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - tailoring-skill/skills/aergia-tailor/scripts/validate-candidate.mjs
  - tailoring-skill/skills/aergia-tailor/scripts/validate-critique.mjs
  - tailoring-skill/tests/candidate.test.mjs
  - tailoring-skill/tests/critique.test.mjs
  - tailoring-skill/tests/session.test.mjs
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-12T16:00:48.889971+00:00'
UPDATED_AT: '2026-09-12T16:00:48.889971+00:00'
---

# FEAT-01M2B44PJKMGCDCTDC13K3Q3JB

## Background

Implemented the skill rubric, critique schema/validator, bounded session loop, stable rich-text IDs, preview relevance and warnings, and submit hash check. Node tests, skill validation, Ruff, and pure API contract/quality tests pass. Full DB-backed tailoring integration remains to run under supported Python 3.12 because the Python 3.14 Alembic test setup hangs during migration startup.

## Investigation

The skill asked the model to compose and preview a complete CV but did not
provide a repeatable critique stage or require the submit helper to verify
that the candidate was unchanged after preview. The backend already had
deterministic relevance and document-quality checks, but exposed them only at
submission. Random rich-text IDs could also make repeated normalization change
a candidate hash.

## Decision

Add a role-calibrated adversarial critique loop to the portable skill and
helper. Keep score calculation deterministic while leaving semantic findings
with the critic. Return relevance and quality findings in preview responses.
Normalize missing rich-text IDs deterministically in the helper and send the
preview hash with submit requests.

## Implementation

Added a strict critique schema and local validator, 100-point rubric, severity
and requirement-gap deductions, five-pass controller, exact candidate/hash
binding, best-candidate preservation, early stop for repeated or stalled
attempts, and explicit fallback review notes. The skill now performs a quick
recruiter scan followed by a close read, prioritizes the weakest two or three
relevant bullets, calibrates expectations to seniority, and distinguishes
supported omissions from unsupported job requirements using the profile,
optional previous CV, and complete Library as evidence. Preview responses now
include relevance and bounded document warnings; page-count warnings ask users
to review length for the role rather than forcing one-page CVs.

## Verification

Passed all tailoring Node tests, skill validation, Ruff, and 12 pure API
quality/contract/bundle tests using ``pytest --noconftest``. The database-backed
test setup was attempted but hangs while Alembic initializes a temporary
SQLite database under Python 3.14; Python 3.12 is not installed here.

## Follow-up

Run ``api/.venv/bin/pytest`` and ``./dev.sh --smoke`` under supported Python
3.12 to exercise the preview/submit hash check through the full ASGI flow.
