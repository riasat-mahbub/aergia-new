---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M356RFPXM9TD7ZSKP4Y63NTK
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  related:
  - FEAT-01M350X71VPND23CHWB2YP7N91
AFFECTS:
  files:
  - api/app/services/tailoring.py
  - api/app/services/tailoring_evaluation.py
  - api/tests/test_tailoring.py
  - api/tests/test_tailoring_evaluation.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - tailoring-skill/tests/session.test.mjs
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-22T18:41:26.750147+00:00'
UPDATED_AT: '2026-09-22T18:41:26.750147+00:00'
---

# Tailoring v5 hardening: authoritative evidence and submission safety

## Background

Harden protocol v5 against Library-only employer false positives, unresolved blocking editorial reviews, and unstable bounded-loop comparisons.

## Investigation

Employer validation compared candidate experience only with the previous CV,
which rejected legitimate Library-only roles. Submission also trusted the
editorial-review shape without enforcing its documented blocking severity.
The local loop used issue IDs alone for unchanged-state detection and used a
candidate hash instead of the latest evaluated pass for exact fallback ties.

## Decision

Treat serialized source and Library rows as one authoritative fact index;
enforce editorial blocking at both helper and server trust boundaries; compare
stable issue state fields; and prefer the latest evaluated pass after all
meaningful safety criteria tie.

## Implementation

Added the pure ``AuthoritativeFactIndex`` and passed frozen Library evidence
through the service boundary. Added Library-only/unsupported employer
regressions, server editorial severity coverage, bounded-loop state-signature
comparison, editorial-block tracking, material revision enforcement, and
latest-pass fallback selection. Added public bundle assertions for the generic
reference Markdown files and kept the protocol version unchanged.

## Verification

Focused tailoring, scanner, frontend, and skill checks passed. The full API
suite passed with 684 tests and one expected skip; Ruff and the external live
smoke gate passed.

## Follow-up
