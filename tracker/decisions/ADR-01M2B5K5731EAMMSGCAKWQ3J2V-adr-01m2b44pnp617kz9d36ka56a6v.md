---
SCHEMA: 4
FORMAT: project-tracker
ID: ADR-01M2B5K5731EAMMSGCAKWQ3J2V
TYPE: adr
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - ADR-01M2B44PNP617KZ9D36KA56A6V
  related:
  - FEAT-01M2B5K5QSDA8BDVRRAATRQ4NW
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
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-12T16:00:48.355461+00:00'
UPDATED_AT: '2026-09-12T16:00:48.355461+00:00'
---

# ADR-01M2B44PNP617KZ9D36KA56A6V

## Background

Implemented the v1 critique decision: a rubric-scored adversarial review of every rendered candidate, deterministic score calculation and 80-point/zero-Critical gate, exact preview-to-submit hash binding, five-pass cap, and flagged best-attempt fallback.

## Investigation

The protocol-v2 agent already writes complete candidates, renders them through
Aergia, and submits unlinked drafts. Its preview returned only a PDF and hash,
leaving semantic review informal. The separate Resume Reviewer skill supplied
useful practices: seniority calibration, requirement-gap classification,
impact and clarity checks, and review of the rendered document. Its fixed
scorecard and document-report workflow do not fit Aergia's editable-candidate
flow.

## Decision

Run a skeptical critic pass after each preview. The critic classifies every
extracted job requirement as present, supported-but-missing, reasonably
inferred, or unsupported using the profile, optional previous CV, and complete
Library as evidence, and records actionable, located findings. A local
controller calculates a 100-point score across job alignment (30), evidence
and credibility (25), impact (20), clarity (15), and rendered presentation
(10). The score passes at 80 or more only when no Critical finding remains.
Finding deductions are 12/5/1 for Critical/Important/Polish; supported-but-
missing requirements cost 15/5/2 points for required/preferred/unknown, and a
missing supported required item is automatically Critical. Category
deductions are capped at their budgets.

Bind each critique and submit to the rendered candidate hash and a stable
local candidate hash. Permit at most five critique passes, stopping earlier
for repeated candidates or stagnation. If no passing attempt remains, the
helper can submit the best reviewed attempt only as an unlinked draft with an
explicit user-facing note. User acceptance remains the only application
linking action. No critique report or document-export format is added.

## Implementation

Implemented in ``FEAT-01M2B5K5QSDA8BDVRRAATRQ4NW``.

## Verification

The local critique controller rejects stale hashes, unknown locations,
duplicate findings, missing requirement classifications, and model-supplied
scores. It calculates the score itself.

## Follow-up

Run the database-backed integration and release smoke checks on supported
Python 3.12; the current Python 3.14 environment hangs during Alembic test
database startup.
